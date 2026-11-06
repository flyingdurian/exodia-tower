"""Persistent, truthful, operator-assisted model task inbox."""
import asyncio, sqlite3, uuid, json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from threading import RLock

def timestamp():return datetime.now(timezone.utc).isoformat()

class TaskCancelled(asyncio.CancelledError):
 """A cancelled task must not receive a late provider callback or result."""

class Inbox:
 def __init__(self,path):
  self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.lock=RLock()
  with self.db() as c:
   c.execute('PRAGMA journal_mode=WAL')
   c.execute("CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, agent_id TEXT, provider TEXT, prompt TEXT, state TEXT, answer TEXT DEFAULT '', artifact TEXT, created_at TEXT, updated_at TEXT)")
   columns={row[1] for row in c.execute("PRAGMA table_info(tasks)")}
   if "error" not in columns:c.execute("ALTER TABLE tasks ADD COLUMN error TEXT DEFAULT ''")
   if "web_research" not in columns:c.execute("ALTER TABLE tasks ADD COLUMN web_research INTEGER DEFAULT 0")
   if "sources" not in columns:c.execute("ALTER TABLE tasks ADD COLUMN sources TEXT DEFAULT '[]'")
   if "metrics" not in columns:c.execute("ALTER TABLE tasks ADD COLUMN metrics TEXT DEFAULT '{}'")
   if "media" not in columns:c.execute("ALTER TABLE tasks ADD COLUMN media TEXT DEFAULT '[]'")
   if "private_instructions" not in columns:c.execute("ALTER TABLE tasks ADD COLUMN private_instructions TEXT DEFAULT ''")
   if "retry_of" not in columns:c.execute("ALTER TABLE tasks ADD COLUMN retry_of TEXT")
   if "retry_index" not in columns:c.execute("ALTER TABLE tasks ADD COLUMN retry_index INTEGER NOT NULL DEFAULT 0")
   c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_retry_of ON tasks(retry_of) WHERE retry_of IS NOT NULL")
   c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_recent ON tasks(created_at DESC, id)")
   c.execute("""CREATE TABLE IF NOT EXISTS task_events(
    id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, event TEXT NOT NULL,
    from_state TEXT, to_state TEXT, occurred_at TEXT NOT NULL)""")
   c.execute("CREATE INDEX IF NOT EXISTS idx_task_events_by_task ON task_events(task_id,id)")
   # A pre-existing task has no historical transitions available. Preserve only
   # a truthful last-known snapshot; never invent prior states or timestamps.
   c.execute("""INSERT INTO task_events(task_id,event,from_state,to_state,occurred_at)
     SELECT t.id,'legacy_snapshot',NULL,t.state,t.updated_at FROM tasks AS t
     WHERE NOT EXISTS(SELECT 1 FROM task_events AS e WHERE e.task_id=t.id)""")
 def db(self):return sqlite3.connect(self.path,timeout=10)
 @staticmethod
 def _mapped(row):
  d=dict(row)
  d['web_research']=bool(d.get('web_research'))
  try:d['sources']=json.loads(d.get('sources') or '[]')
  except (TypeError,ValueError):d['sources']=[]
  try:d['metrics']=json.loads(d.get('metrics') or '{}')
  except (TypeError,ValueError):d['metrics']={}
  try:d['media']=json.loads(d.get('media') or '[]')
  except (TypeError,ValueError):d['media']=[]
  d['retry_index']=int(d.get('retry_index') or 0)
  return d
 @staticmethod
 def _event(c,task_id,event,from_state,to_state):
  c.execute("INSERT INTO task_events(task_id,event,from_state,to_state,occurred_at) VALUES(?,?,?,?,?)",
            (task_id,event,from_state,to_state,timestamp()))
 def get(self,id):
  with self.lock,self.db() as c:
   c.row_factory=sqlite3.Row;r=c.execute("SELECT * FROM tasks WHERE id=?",(id,)).fetchone()
  if r is None:raise KeyError(id)
  return self._mapped(r)
 def list(self):
  with self.lock,self.db() as c:
   c.row_factory=sqlite3.Row;rows=c.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 75").fetchall()
  return [self._mapped(x) for x in rows]
 def create(self,agent,provider,prompt,web_research=False,private_instructions=''):
  if provider not in ('ollama','custom_web','web_slot_2','web_slot_3','chatgpt','gemini','deepseek'):raise ValueError("Unsupported model")
  if not prompt.strip() or len(prompt)>12000:raise ValueError("Prompt length invalid")
  if not isinstance(private_instructions,str) or len(private_instructions)>4000:raise ValueError("Invalid private instructions")
  id=str(uuid.uuid4());now=timestamp()
  with self.lock,self.db() as c:
   c.execute("INSERT INTO tasks(id,agent_id,provider,prompt,state,created_at,updated_at,web_research,sources,private_instructions) VALUES(?,?,?,?,?,?,?,?,?,?)",
             (id,agent,provider,prompt.strip(),'draft',now,now,int(web_research),'[]',private_instructions.strip()))
   self._event(c,id,'created',None,'draft')
  return self.get(id)
 def update(self,id,key,value):
  if key not in ('answer','state','artifact','error','sources','metrics','media'):raise ValueError("Forbidden update")
  if key=='sources':
   if not isinstance(value,list) or len(value)>4:raise ValueError("Invalid evidence links")
   value=json.dumps(value)
  elif key=='metrics':
   if not isinstance(value,dict) or len(value)>20:raise ValueError("Invalid task timing metrics")
   value=json.dumps(value)
  elif key=='media':
   if not isinstance(value,list) or len(value)>4:raise ValueError("Invalid media list")
   for record in value:
    if not isinstance(record,dict):raise ValueError("Invalid media record")
    path=record.get('url','')
    if path and (not isinstance(path,str) or not path.startswith('/artifacts/') or '..' in path):
     raise ValueError("Invalid media artifact URL")
   value=json.dumps(value)
  with self.lock,self.db() as c:
   row=c.execute('SELECT state FROM tasks WHERE id=?',(id,)).fetchone()
   if row is None:raise KeyError(id)
   current=row[0]
   if current in ('cancelled','failed'):
    raise TaskCancelled('Terminal task; late provider callback rejected')
   if current=='answered' and key not in ('artifact',):
    raise TaskCancelled('Answered task cannot be changed by a late callback')
   if key=='state' and (not isinstance(value,str) or not value or len(value)>64):
    raise ValueError('Invalid task state')
   c.execute(f"UPDATE tasks SET {key}=?,updated_at=? WHERE id=?",(value,timestamp(),id))
   if key=='state' and current!=value:
    self._event(c,id,'state_change',current,value)
  return self.get(id)

 def cancel(self,id):
  """Atomically stop local task delivery without implying remote cancellation."""
  with self.lock,self.db() as c:
   row=c.execute('SELECT state FROM tasks WHERE id=?',(id,)).fetchone()
   if row is None:raise KeyError(id)
   state=row[0]
   if state in ('answered','failed'):
    raise ValueError('Completed or failed tasks cannot be cancelled')
   if state!='cancelled':
    c.execute("UPDATE tasks SET state='cancelled',error=?,updated_at=? WHERE id=?",(
      'Cancelled locally. An already-submitted remote provider request may still finish outside Exodia.',
      timestamp(),id))
    self._event(c,id,'cancelled',state,'cancelled')
  return self.get(id)

 def fail_interrupted(self):
  """Mark interrupted jobs failed on boot without losing historical snapshots."""
  active=('running','researching','queued','cooldown','opening','typing','submitting',
          'waiting_for_reply','rendering_media')
  with self.lock,self.db() as c:
   rows=c.execute("SELECT id,state,provider FROM tasks").fetchall()
   for task_id,state,provider in rows:
    if state in active or (provider=='chatgpt' and state=='awaiting_operator'):
     message=('ChatGPT browser review tab was closed by Exodia restart. Recreate the task.'
              if state=='awaiting_operator' else
              'Interrupted by Exodia restart. Use an explicit new retry attempt.')
     c.execute("UPDATE tasks SET state='failed',error=?,updated_at=? WHERE id=?",
               (message,timestamp(),task_id))
     self._event(c,task_id,'restart_interrupted',state,'failed')

 def retry(self,id,max_retries=3):
  """Atomically create or find one linked retry; never dispatch a provider here.

  A duplicate request returns the same successor, so double-clicking cannot
  create multiple browser submissions. Follow a failed successor to retry again.
  """
  if not isinstance(max_retries,int) or max_retries<1 or max_retries>10:
   raise ValueError('Invalid retry policy')
  with self.lock,self.db() as c:
   c.row_factory=sqlite3.Row
   parent=c.execute('SELECT * FROM tasks WHERE id=?',(id,)).fetchone()
   if parent is None:raise KeyError(id)
   existing=c.execute('SELECT * FROM tasks WHERE retry_of=?',(id,)).fetchone()
   if existing is not None:return self._mapped(existing),False
   if parent['state'] not in ('failed','cancelled'):
    raise ValueError('Only failed or cancelled tasks may be retried')
   idx=int(parent['retry_index'] or 0)
   if idx>=max_retries:raise ValueError('Retry limit reached')
   next_id=str(uuid.uuid4());now=timestamp()
   c.execute("""INSERT INTO tasks(
     id,agent_id,provider,prompt,state,answer,created_at,updated_at,
     web_research,sources,metrics,media,private_instructions,retry_of,retry_index)
     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
     (next_id,parent['agent_id'],parent['provider'],parent['prompt'],'draft','',
      now,now,parent['web_research'],'[]','{}','[]',
      parent['private_instructions'],id,idx+1))
   self._event(c,id,'retry_requested',parent['state'],parent['state'])
   self._event(c,next_id,'retry_created',None,'draft')
  return self.get(next_id),True

 def events(self,id,limit=200):
  """Durable, non-secret state timeline for the selected task."""
  if not isinstance(limit,int) or not 1<=limit<=500:
   raise ValueError('Invalid events limit')
  self.get(id)
  with self.lock,self.db() as c:
   c.row_factory=sqlite3.Row
   rows=c.execute("""SELECT id,task_id,event,from_state,to_state,occurred_at
                     FROM task_events WHERE task_id=? ORDER BY id ASC LIMIT ?""",
                  (id,limit)).fetchall()
  return [dict(row) for row in rows]

 def list_page(self,limit=50,offset=0):
  """Paginated persistent records; private instructions never reach HTTP."""
  if (not isinstance(limit,int) or not 1<=limit<=200 or
      not isinstance(offset,int) or offset<0 or offset>1000000):
   raise ValueError('Invalid pagination')
  with self.lock,self.db() as c:
   c.row_factory=sqlite3.Row
   rows=c.execute("SELECT * FROM tasks ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?",
                  (limit,offset)).fetchall()
   total=c.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]
  return {'tasks':[self._mapped(row) for row in rows], 'total':total,
          'limit':limit,'offset':offset}

 def cleanup_stale(self,maximum_idle_seconds=3600,now=None):
  """Fail genuinely stalled active states; prevent late results overwriting them.

  An operator-owned draft or manual handoff is not automatically expired.
  The caller cancels local asyncio jobs for returned IDs. A consumer browser
  request may still finish remotely, never claim it was revoked.
  """
  if not isinstance(maximum_idle_seconds,(int,float)) or not 60<=maximum_idle_seconds<=86400:
   raise ValueError('Invalid stale cleanup threshold')
  now=now or datetime.now(timezone.utc)
  if now.tzinfo is None:raise ValueError('now must include timezone')
  cutoff=now.astimezone(timezone.utc)-timedelta(seconds=maximum_idle_seconds)
  active=('running','researching','queued','cooldown','opening','typing',
          'submitting','waiting_for_reply','rendering_media')
  expired=[]
  with self.lock,self.db() as c:
   rows=c.execute("SELECT id,state,updated_at FROM tasks WHERE state IN ("+
                  ",".join("?" for _ in active)+")",active).fetchall()
   for task_id,state,last in rows:
    try:updated=datetime.fromisoformat(last).astimezone(timezone.utc)
    except (ValueError,TypeError,AttributeError):continue
    if updated.tzinfo is None:continue
    if updated > cutoff:continue
    c.execute("UPDATE tasks SET state='failed',error=?,updated_at=? WHERE id=? AND state=?",
              ('Stale task stopped locally; the external provider may continue. Retry explicitly.',
               timestamp(),task_id,state))
    if c.execute('SELECT changes()').fetchone()[0]:
     self._event(c,task_id,'stale_cleanup',state,'failed')
     expired.append(task_id)
  return expired
