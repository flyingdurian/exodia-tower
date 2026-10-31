"""Persistent, truthful, operator-assisted model task inbox."""
import sqlite3, uuid
from pathlib import Path
from datetime import datetime, timezone
from threading import RLock

def timestamp():return datetime.now(timezone.utc).isoformat()
class Inbox:
 def __init__(self,path):
  self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.lock=RLock()
  with self.db() as c:c.execute("CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, agent_id TEXT, provider TEXT, prompt TEXT, state TEXT, answer TEXT DEFAULT '', artifact TEXT, created_at TEXT, updated_at TEXT)")
 def db(self):return sqlite3.connect(self.path,timeout=10)
 def get(self,id):
  with self.lock,self.db() as c:
   c.row_factory=sqlite3.Row;r=c.execute("SELECT * FROM tasks WHERE id=?",(id,)).fetchone()
  if r is None:raise KeyError(id)
  return dict(r)
 def list(self):
  with self.lock,self.db() as c:
   c.row_factory=sqlite3.Row;rows=c.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 75").fetchall()
  return [dict(x) for x in rows]
 def create(self,agent,provider,prompt):
  if provider not in ('chatgpt','gemini','deepseek'):raise ValueError("Unsupported model")
  if not prompt.strip() or len(prompt)>12000:raise ValueError("Prompt length invalid")
  id=str(uuid.uuid4());now=timestamp()
  with self.lock,self.db() as c:c.execute("INSERT INTO tasks(id,agent_id,provider,prompt,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",(id,agent,provider,prompt.strip(),'draft',now,now))
  return self.get(id)
 def update(self,id,key,value):
  if key not in ('answer','state','artifact'):raise ValueError("Forbidden update")
  self.get(id)
  with self.lock,self.db() as c:c.execute(f"UPDATE tasks SET {key}=?,updated_at=? WHERE id=?",(value,timestamp(),id))
  return self.get(id)
