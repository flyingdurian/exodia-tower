"""SQLite FTS5 hybrid search + optional local sqlite-vec dense index."""
from __future__ import annotations
import re
import sqlite3
from pathlib import Path
from threading import Lock

EXTENSIONS = {'.py','.md','.txt','.json','.yaml','.yml','.js','.ts','.html','.css','.toml'}
SKIP_DIRS = {'.git', '.venv', 'venv', 'node_modules', 'session_data', 'app_data',
             'debug_snapshots', '__pycache__', '.pytest_cache'}

class CrystalArchives:
    def __init__(self, db: Path, root: Path, dense: bool = False):
        self.db = db
        self.root = root.resolve()
        self.lock = Lock()
        self._model = None
        self.dense = False
        db.parent.mkdir(parents=True, exist_ok=True)
        self._init(dense)

    def _connect(self):
        cx = sqlite3.connect(self.db, timeout=15)
        if self.dense:
            import sqlite_vec
            cx.enable_load_extension(True)
            sqlite_vec.load(cx)
            cx.enable_load_extension(False)
        return cx

    def _init(self, dense: bool):
        if dense:
            try:
                import sqlite_vec  # noqa
                import sentence_transformers  # noqa
                self.dense = True
            except ImportError:
                pass
        with self._connect() as cx:
            cx.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(source UNINDEXED, content, tokenize='porter unicode61')")
            if self.dense:
                cx.execute('CREATE VIRTUAL TABLE IF NOT EXISTS docs_vec USING vec0(embedding float[384])')

    def _embed(self, text: str):
        if not self.dense:
            return None
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        import sqlite_vec
        data = self._model.encode(text, normalize_embeddings=True)
        return sqlite_vec.serialize_float32(data.tolist())

    @staticmethod
    def _chunks(content: str, size: int = 1350, overlap: int = 170):
        for pos in range(0, len(content), size-overlap):
            chunk = content[pos:pos+size]
            if chunk.strip():
                yield chunk
            if pos+size >= len(content):
                break

    def add_document(self, source: str, content: str) -> int:
        if not source.strip():
            raise ValueError('Missing source')
        if len(content) > 525_000:
            raise ValueError('Document too large for MVP')
        with self.lock, self._connect() as cx:
            old_ids = [r[0] for r in cx.execute('SELECT rowid FROM docs_fts WHERE source LIKE ?', (source + '#%',))]
            if self.dense:
                for rowid in old_ids:
                    cx.execute('DELETE FROM docs_vec WHERE rowid=?', (rowid,))
            cx.execute('DELETE FROM docs_fts WHERE source LIKE ?', (source + '#%',))
            count = 0
            for i, chunk in enumerate(self._chunks(content)):
                cur = cx.execute('INSERT INTO docs_fts(source, content) VALUES (?,?)', (f'{source}#{i}', chunk))
                if self.dense:
                    cx.execute('INSERT INTO docs_vec(rowid, embedding) VALUES (?, ?)',
                               (cur.lastrowid, self._embed(chunk)))
                count += 1
        return count

    def index_tree(self, max_files: int = 400) -> dict:
        added, chunks, errors = 0, 0, 0
        for file in self.root.rglob('*'):
            if added >= max_files:
                break
            try:
                relative = file.relative_to(self.root)
                if any(x.startswith('.') or x in SKIP_DIRS for x in relative.parts[:-1]):
                    continue
                if file.is_symlink() or not file.is_file() or file.suffix.lower() not in EXTENSIONS:
                    continue
                if file.name.startswith('.') or file.stat().st_size > 512_000:
                    continue
                content = file.read_text(encoding='utf-8', errors='replace')
                chunks += self.add_document(relative.as_posix(), content)
                added += 1
            except (OSError, UnicodeError, ValueError, sqlite3.Error):
                errors += 1
        return {'files': added, 'chunks': chunks, 'errors': errors,
                'dense_enabled': self.dense}

    def search(self, question: str, limit: int = 5) -> list[dict]:
        tokens = re.findall(r'[\w]{2,}', question.lower())[:12]
        if not tokens:
            return []
        # Phrase quote each token to keep FTS expressions safe.
        match = ' OR '.join('"' + t.replace('"', '') + '"' for t in tokens)
        with self._connect() as cx:
            lexical = cx.execute('''SELECT rowid, source, snippet(docs_fts, 1, '', '', ' … ', 36), bm25(docs_fts)
                                    FROM docs_fts WHERE docs_fts MATCH ?
                                    ORDER BY bm25(docs_fts) LIMIT ?''', (match, limit*3)).fetchall()
            combined = {r[0]: {'source': r[1], 'snippet': r[2], 'score': round(-r[3], 3)} for r in lexical}
            if self.dense:
                import sqlite_vec
                rows = cx.execute('''SELECT rowid, distance FROM docs_vec
                                    WHERE embedding MATCH ? AND k = ? ORDER BY distance''',
                                  (self._embed(question), limit*3)).fetchall()
                for rowid, dist in rows:
                    if rowid not in combined:
                        row = cx.execute('SELECT source, substr(content,1,400) FROM docs_fts WHERE rowid=?', (rowid,)).fetchone()
                        if row:
                            combined[rowid] = {'source': row[0], 'snippet': row[1], 'score': 0}
                    if rowid in combined:
                        combined[rowid]['score'] += max(0.0, 1.0-float(dist)) * 5
            results = sorted(combined.values(), key=lambda r: r['score'], reverse=True)
            return results[:limit]

    def count(self) -> int:
        with self._connect() as cx:
            return cx.execute('SELECT count(*) FROM docs_fts').fetchone()[0]
