"""Deterministic editorial planning: draft only, never publish."""
from __future__ import annotations
from .models import ContentJob, Platform

def create_brief(title: str, platforms: set[Platform], sources: list[str] | None = None) -> dict:
    if not title.strip(): raise ValueError('Title is required')
    if not platforms: raise ValueError('Select at least one platform')
    job=ContentJob(title=title.strip(),platforms=platforms,source_urls=sources or [])
    return {
        'job_id':job.id,'title':job.title,'stage':job.stage.value,
        'platforms':sorted(p.value for p in platforms),
        'research_questions':[
            'Who is the audience and what problem is solved?',
            'Which claims require citations, rights clearance, or further evidence?',
            'Which opening hook and visual demonstration retain attention?',
            'How do format, title, captions and call to action change by platform?'],
        'review_required':True,'publication_status':'not_published',
        'metrics_status':'not_connected'
    }
