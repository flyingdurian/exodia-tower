"""Persistent, truthful, operator-assisted model task inbox."""
import sqlite3, uuid, json
from pathlib import Path
from datetime import datetime, timezone
from threading import RLock

def timestamp():return datetime.now(timezone.utc).isoformat()
class Inbox:
 def __init__(self,path):
  self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.lock=RLock()
  with self.db() as c:
   c.execute("CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, agent_id TEXT, provider TEXT, prompt TEXT, state TEXT, answer TEXT DEFAULT '', artifact TEXT, created_at TEXT, updated_at TEXT)")
   columns={row[1] for row in c.execute("PRAGMA table_info(tasks)")}
   if "error" not in columns:c.execute("ALTER TABLE tasks ADD COLUMN error TEXT DEFAULT ''")
   if "web_research" not in columns:c.execute("ALTER TABLE tasks ADD COLUMN web_research INTEGER DEFAULT 0")
   if "sources" not in columns:c.execute("ALTER TABLE tasks ADD COLUMN sources TEXT DEFAULT '[]'")
 def db(self):return sqlite3.connect(self.path,timeout=10)
 @staticmethod
 def _mapped(row):
  d=dict(row)
  d['web_research']=bool(d.get('web_research'))
  try:d['sources']=json.loads(d.get('sources') or '[]')
  except (TypeError,ValueError):d['sources']=[]
  return d
 def get(self,id):
  with self.lock,self.db() as c:
   c.row_factory=sqlite3.Row;r=c.execute("SELECT * FROM tasks WHERE id=?",(id,)).fetchone()
  if r is None:raise KeyError(id)
  return self._mapped(r)
 def list(self):
  with self.lock,self.db() as c:
   c.row_factory=sqlite3.Row;rows=c.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 75").fetchall()
  return [self._mapped(x) for x in rows]
 def create(self,agent,provider,prompt,web_research=False):
  if provider not in ('ollama','chatgpt','gemini','deepseek'):raise ValueError("Unsupported model")
  if not prompt.strip() or len(prompt)>12000:raise ValueError("Prompt length invalid")
  id=str(uuid.uuid4());now=timestamp()
  with self.lock,self.db() as c:c.execute("INSERT INTO tasks(id,agent_id,provider,prompt,state,created_at,updated_at,web_research,sources) VALUES(?,?,?,?,?,?,?,?,?)",(id,agent,provider,prompt.strip(),'draft',now,now,int(web_research),'[]'))
  return self.get(id)
 def update(self,id,key,value):
  if key not in ('answer','state','artifact','error','sources'):raise ValueError("Forbidden update")
  self.get(id)
  if key=='sources':
   if not isinstance(value,list) or len(value)>4:raise ValueError("Invalid evidence links")
   value=json.dumps(value)
  with self.lock,self.db() as c:c.execute(f"UPDATE tasks SET {key}=?,updated_at=? WHERE id=?",(value,timestamp(),id))
  return self.get(id)

 def fail_interrupted(self):
  """Prevent stale 'working' UI after application restart."""
  with self.lock,self.db() as c:
   c.execute("UPDATE tasks SET state='failed',error='Interrupted by Exodia restart. Create a new task to retry.',updated_at=? WHERE state IN ('running','researching')",(timestamp(),))
