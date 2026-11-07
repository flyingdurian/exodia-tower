"""Phase 17 read-only audit of local operator DAG, task index and recovery lineage.

No art, provider, publish or data mutation. Partial scans never claim full
integrity. Only bounded counts and stable status codes leave this module.
"""
from __future__ import annotations
import json
import re
import sqlite3
from pathlib import Path
from app.operations.workflow_plans import AGENTS, SCHEMA as PLAN_SCHEMA

SCHEMA="exodia.phase17.workflow-integrity/v1"
LIMITS=(100,500,200)
CODES=("invalid_document","link_index_mismatch","orphan_link",
       "missing_task","owner_mismatch","review_drift","invalid_lineage")
KEY=re.compile(r"^[a-z][a-z0-9_]{0,31}$")
TASK=re.compile(r"^[A-Za-z0-9-]{1,128}$")


def audit_workflows(store,inbox):
    path=Path(store.path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Unsafe local workflow database")
    failures={k:0 for k in CODES}
    with sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro",
                         uri=True,timeout=5) as conn:
        if conn.execute("PRAGMA quick_check(1)").fetchone()!=("ok",):
            raise ValueError("Workflow SQLite integrity failure")
        total=conn.execute("SELECT COUNT(*) FROM operator_workflows").fetchone()[0]
        total_links=conn.execute(
            "SELECT COUNT(*) FROM operator_workflow_task_links").fetchone()[0]
        docs=conn.execute("SELECT id,document FROM operator_workflows "
            "ORDER BY updated_at DESC,id DESC LIMIT ?",(LIMITS[0],)).fetchall()
        links=conn.execute("SELECT task_id,workflow_id,step_key "
            "FROM operator_workflow_task_links ORDER BY task_id LIMIT ?",
            (LIMITS[1],)).fetchall()
        has_lineage=conn.execute("SELECT 1 FROM sqlite_master "
            "WHERE type='table' AND name='operator_workflow_recovery'").fetchone()
        total_forks=conn.execute("SELECT COUNT(*) FROM operator_workflow_recovery"
            ).fetchone()[0] if has_lineage else 0
        forks=conn.execute("SELECT source_workflow_id,source_revision,"
            "new_workflow_id,reason_code FROM operator_workflow_recovery "
            "ORDER BY source_workflow_id,source_revision LIMIT ?",
            (LIMITS[2],)).fetchall() if has_lineage else []
        sample_partial=(total>len(docs) or total_links>len(links)
                        or total_forks>len(forks))
        parsed={}
        for identity,raw in docs:
            try:
                doc=json.loads(raw)
                if (not isinstance(doc,dict) or doc.get("schema")!=PLAN_SCHEMA
                    or doc.get("id")!=identity
                    or doc.get("status") not in ("operator_planning","reviewed_local_only")
                    or type(doc.get("revision")) is not int or doc["revision"]<1
                    or not isinstance(doc.get("steps"),list)
                    or not 1<=len(doc["steps"])<=12):
                    raise ValueError("invalid plan")
                seen=set()
                task_links={}
                for step in doc["steps"]:
                    if (not isinstance(step,dict)
                        or not isinstance(step.get("key"),str)
                        or not KEY.fullmatch(step["key"])
                        or step["key"] in seen
                        or step.get("agent_id") not in AGENTS
                        or not isinstance(step.get("label"),str)
                        or not isinstance(step.get("depends_on"),list)
                        or any(not isinstance(k,str) or k not in seen
                               for k in step["depends_on"])
                        or len(set(step["depends_on"]))!=len(step["depends_on"])):
                        raise ValueError("invalid DAG")
                    seen.add(step["key"])
                    task_id=step.get("linked_task_id")
                    if task_id is not None:
                        if (not isinstance(task_id,str)
                            or not TASK.fullmatch(task_id)
                            or task_id in task_links):
                            raise ValueError("invalid task link")
                        task_links[task_id]=(step["key"],step["agent_id"])
                parsed[identity]=task_links
                if doc["status"]=="reviewed_local_only" and len(task_links)!=len(doc["steps"]):
                    failures["review_drift"]+=1
                for task_id,(key,agent) in task_links.items():
                    index=conn.execute("SELECT workflow_id,step_key "
                        "FROM operator_workflow_task_links WHERE task_id=?",
                        (task_id,)).fetchone()
                    if index!=(identity,key):
                        failures["link_index_mismatch"]+=1
                    try:
                        task=inbox.get(task_id)
                    except (KeyError,ValueError):
                        failures["missing_task"]+=1
                        continue
                    if task.get("agent_id")!=agent:
                        failures["owner_mismatch"]+=1
                    if (doc["status"]=="reviewed_local_only"
                        and task.get("state")!="answered"):
                        failures["review_drift"]+=1
            except (ValueError,TypeError,KeyError,AttributeError):
                failures["invalid_document"]+=1
        for task_id,wid,key in links:
            if wid in parsed:
                if task_id not in parsed[wid] or parsed[wid][task_id][0]!=key:
                    failures["link_index_mismatch"]+=1
            elif conn.execute("SELECT 1 FROM operator_workflows WHERE id=?",
                              (wid,)).fetchone() is None:
                failures["orphan_link"]+=1
        for origin,revision,child,reason in forks:
            if (not isinstance(origin,str) or not isinstance(child,str)
                or origin==child or type(revision) is not int or revision<1
                or reason not in ("linked_task_failed","reviewed_plan_revision")):
                failures["invalid_lineage"]+=1
                continue
            a=conn.execute("SELECT document FROM operator_workflows WHERE id=?",
                           (origin,)).fetchone()
            b=conn.execute("SELECT document FROM operator_workflows WHERE id=?",
                           (child,)).fetchone()
            try:
                first=json.loads(a[0]) if a else {}
                second=json.loads(b[0]) if b else {}
                if (first.get("schema")!=PLAN_SCHEMA
                    or second.get("schema")!=PLAN_SCHEMA
                    or first.get("revision",0)<revision
                    or second.get("id")!=child):
                    failures["invalid_lineage"]+=1
            except (ValueError,TypeError,AttributeError):
                failures["invalid_lineage"]+=1
    bad=sum(failures.values())
    return {"schema":SCHEMA,"read_only":True,
            "status":("requires_operator_review" if bad else
                      "partial_sample" if sample_partial else "sample_consistent"),
            "total_plans":total,"total_task_links":total_links,
            "total_recovery_forks":total_forks,
            "sampled_plans":len(docs),"sampled_links":len(links),
            "sampled_recovery_forks":len(forks),
            "sampling_incomplete":sample_partial,
            "failure_counts":failures,"total_failures":bad,
            "owner_review_required":bad>0 or sample_partial,
            "provider_authentication_verified":False,
            "native_art_approved":False,
            "external_dispatch_performed":False,
            "social_publishing_performed":False,
            "production_release_enabled":False}
