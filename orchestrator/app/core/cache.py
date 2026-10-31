"""SQLite exact-cache with TTL and explicit namespace boundaries.

Dense semantic matching can be enabled in RAG; exact cache avoids accidental
reuse of stale or private answers. Never cache inbox content or live metrics.
"""
import hashlib
import re
import sqlite3
import time
from pathlib import Path


def canonical(question: str) -> str:
    return re.sub(r'\s+', ' ', question.casefold().strip())


class SpeedrunnerCache:
    def __init__(self, db: Path):
        self.db = db
        db.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as cx:
            cx.execute('''CREATE TABLE IF NOT EXISTS answer_cache (
                key TEXT PRIMARY KEY, question TEXT NOT NULL,
                namespace TEXT NOT NULL, answer TEXT NOT NULL, expires REAL NOT NULL
            )''')

    def _connect(self):
        return sqlite3.connect(self.db, timeout=10)

    def _key(self, namespace: str, prompt: str) -> str:
        return hashlib.sha256((namespace + '\0' + canonical(prompt)).encode()).hexdigest()

    def get(self, namespace: str, prompt: str) -> str | None:
        with self._connect() as cx:
            row = cx.execute('SELECT answer, expires FROM answer_cache WHERE key=?',
                             (self._key(namespace, prompt),)).fetchone()
            if row and row[1] > time.time():
                return row[0]
            if row:
                cx.execute('DELETE FROM answer_cache WHERE key=?', (self._key(namespace, prompt),))
        return None

    def put(self, namespace: str, prompt: str, answer: str, ttl_seconds: int = 3600):
        with self._connect() as cx:
            cx.execute('''INSERT OR REPLACE INTO answer_cache (key, question, namespace, answer, expires)
                        VALUES (?,?,?,?,?)''', (self._key(namespace, prompt),
                                                canonical(prompt), namespace, answer,
                                                time.time() + ttl_seconds))

    def clear(self) -> None:
        with self._connect() as cx:
            cx.execute('DELETE FROM answer_cache')

    def count(self) -> int:
        with self._connect() as cx:
            return cx.execute('SELECT count(*) FROM answer_cache WHERE expires > ?', (time.time(),)).fetchone()[0]
