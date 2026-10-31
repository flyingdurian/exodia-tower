"""Persistent, approval-gated editorial queue for three distinct platforms."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from threading import RLock
from uuid import uuid4

PLATFORMS = frozenset({'youtube', 'tiktok', 'instagram'})
STAGES = ('idea', 'research', 'script', 'assets', 'edit', 'review', 'approved',
          'scheduled', 'published', 'monitored')
EDITABLE = frozenset({'title', 'concept', 'script', 'caption', 'notes', 'source_urls',
                      'platforms', 'media_path', 'scheduled_for'})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkflowError(ValueError):
    pass


class EditorialStore:
    """SQLite local-first store; no mock analytics and no simulated posting."""
    def __init__(self, db: Path):
        self.db = Path(db)
        self.db.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        with self._connect() as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS social_jobs
                (id TEXT PRIMARY KEY, document TEXT NOT NULL, updated_at TEXT NOT NULL)''')

    def _connect(self):
        return sqlite3.connect(self.db, timeout=10)

    def _save(self, job: dict):
        job['updated_at'] = utc_now()
        with self._connect() as c:
            c.execute('INSERT OR REPLACE INTO social_jobs(id, document, updated_at) VALUES(?,?,?)',
                      (job['id'], json.dumps(job, ensure_ascii=False), job['updated_at']))
        return job

    def list(self, limit: int = 100) -> list[dict]:
        with self.lock, self._connect() as c:
            rows = c.execute('SELECT document FROM social_jobs ORDER BY updated_at DESC LIMIT ?',
                             (max(1, min(limit, 100)),)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def get(self, job_id: str) -> dict:
        with self.lock, self._connect() as c:
            row = c.execute('SELECT document FROM social_jobs WHERE id=?', (job_id,)).fetchone()
        if not row:
            raise KeyError('Unknown editorial job')
        return json.loads(row[0])

    @staticmethod
    def _platforms(values) -> list[str]:
        if not isinstance(values, list) or not values or any(p not in PLATFORMS for p in values):
            raise WorkflowError('Choose one or more supported platforms')
        return sorted(set(values))

    @staticmethod
    def _sources(values) -> list[str]:
        if not isinstance(values, list) or len(values) > 12 or any(
                not isinstance(x, str) or not x.startswith('https://') or len(x) > 500
                for x in values):
            raise WorkflowError('Sources must be HTTPS URLs (12 maximum)')
        return values

    def create(self, title: str, platforms: list[str], concept: str = '',
               source_urls: list[str] | None = None) -> dict:
        if not title or not title.strip() or len(title) > 160:
            raise WorkflowError('Title must be 1–160 characters')
        if len(concept) > 4000:
            raise WorkflowError('Concept exceeds limit')
        job = dict(id=str(uuid4()), title=title.strip(), platforms=self._platforms(platforms),
                   concept=concept, script='', caption='', notes='',
                   source_urls=self._sources(source_urls or []), media_path='', scheduled_for='',
                   stage='idea', approval=None, published_url=None, published_at=None,
                   analytics={'status':'not_connected', 'data':None},
                   audit=[dict(at=utc_now(), action='created')], updated_at=utc_now())
        with self.lock:
            return self._save(job)

    def update(self, job_id: str, patch: dict) -> dict:
        unknown = set(patch) - EDITABLE
        if unknown or not patch:
            raise WorkflowError('Unsupported or empty update')
        with self.lock:
            job = self.get(job_id)
            if job['stage'] in ('published','monitored'):
                raise WorkflowError('Published records cannot be edited')
            for key, value in patch.items():
                if key == 'platforms': value = self._platforms(value)
                elif key == 'source_urls': value = self._sources(value)
                elif not isinstance(value, str) or len(value) > (160 if key=='title' else 12000):
                    raise WorkflowError(f'Invalid value for {key}')
                if key == 'title' and not value.strip():
                    raise WorkflowError('Title must not be empty')
                job[key] = value
            if job['approval']:
                job['approval'] = None
                job['stage'] = 'review'
                job['audit'].append(dict(at=utc_now(),action='approval_revoked_on_edit'))
            job['audit'].append(dict(at=utc_now(), action='updated', fields=sorted(patch)))
            return self._save(job)

    def advance(self, job_id: str, next_stage: str) -> dict:
        with self.lock:
            job = self.get(job_id)
            old = job['stage']
            if next_stage not in STAGES or STAGES.index(next_stage) != STAGES.index(old) + 1:
                raise WorkflowError('Stages advance sequentially')
            if next_stage in {'approved', 'scheduled', 'published', 'monitored'}:
                raise WorkflowError('Approval, scheduling and publishing require their own authenticated gates')
            job['stage'] = next_stage
            job['audit'].append(dict(at=utc_now(), action='advanced',from_stage=old,to_stage=next_stage))
            return self._save(job)

    @staticmethod
    def _fingerprint(job: dict) -> str:
        data = {k:job[k] for k in ('title','platforms','script','caption','media_path','scheduled_for')}
        return sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def approve(self, job_id: str, confirmation: str) -> dict:
        with self.lock:
            job = self.get(job_id)
            if job['stage'] != 'review' or confirmation != 'APPROVE CONTENT':
                raise WorkflowError('Review stage and explicit confirmation are required')
            if not job['script'].strip():
                raise WorkflowError('A script must be reviewed before approval')
            job['approval'] = dict(at=utc_now(), actor='local operator', fingerprint=self._fingerprint(job))
            job['stage'] = 'approved'
            job['audit'].append(dict(at=utc_now(), action='approved_for_future_submission'))
            return self._save(job)

    def brief(self, job_id: str) -> dict:
        job = self.get(job_id)
        return {'job_id':job_id,'status':'template_only',
                'research_questions':[
                    'Who is the audience and what question does this answer?',
                    'Which claims require authoritative evidence and dates?',
                    'What is the first two-second visual hook?',
                    'Which segments should be recut for each platform?'],
                'platform_notes': {
                    'youtube':'Plan title, thumbnail, retention hook and description; check Analytics API access.',
                    'tiktok':'Plan a mobile-first hook and on-screen captions; check Content Posting API eligibility.',
                    'instagram':'Prepare a Reel-safe cut and account-appropriate caption; confirm professional-account permissions.'},
                'sources_supplied':len(job['source_urls']),
                'analytics_status':'not_connected','publishing_status':'not_connected'}

    def summary(self) -> dict:
        jobs = self.list()
        return {'total':len(jobs),
                'by_stage':{stage:sum(j['stage']==stage for j in jobs) for stage in STAGES},
                'platforms':{p:sum(p in j['platforms'] for j in jobs) for p in sorted(PLATFORMS)},
                'publishing':'disabled_pending_oauth','analytics':'not_connected'}
