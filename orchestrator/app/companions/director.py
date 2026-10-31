"""Stateful UI companion direction. No fictional AI agents or unauthorized tools."""
from __future__ import annotations
import json
from pathlib import Path
from threading import RLock

STATES=frozenset({'idle','thinking','working','success','rest','alert'})

class CompanionDirector:
    def __init__(self, root: Path, events):
        self.agents = json.loads((root/'app'/'companions'/'roster.json').read_text(encoding='utf-8'))
        self.known={a['id'] for a in self.agents}
        self.state={a['id']:'idle' for a in self.agents}
        self._lock=RLock()
        self.events=events
        clips_root=root/'frontend'/'companions'/'clips'
        for agent in self.agents:
            agent['clips']={}
            for s in STATES:
                for ext in ('.webm','.mp4'):
                    if (clips_root/agent['id']/(s+ext)).is_file():
                        agent['clips'][s]=f'/assets/companions/clips/{agent["id"]}/{s}{ext}'
                        break

    def react(self, agent_id: str, mood: str):
        if agent_id not in self.known: raise ValueError('Unknown companion')
        if mood not in STATES: raise ValueError('Unknown companion state')
        with self._lock:
            self.state[agent_id]=mood
        self.events.publish('companion',f'{agent_id} changed state', f'{agent_id}:{mood}')
        return {'agent_id':agent_id,'state':mood}

    def snapshot(self):
        with self._lock:return dict(self.state)
