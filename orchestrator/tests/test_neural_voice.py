"""Natural local TTS proxy: no remote network, agent-scoped voice selection."""
from fastapi.testclient import TestClient
from app.api import server

class AudioResult:
    status_code=200
    content=b"ID3fake-mp3"
    headers={'content-type':'audio/mpeg'}
    def raise_for_status(self):pass
class FakeLocalTTS:
    def __init__(self,*args,**kwargs):self.calls=[]
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    async def post(self,url,json):
        assert url=='http://127.0.0.1:8880/v1/audio/speech'
        assert json['voice']=='af_heart'
        assert json['input']=='Hello world'
        return AudioResult()
    async def get(self,url):
        assert url=='http://127.0.0.1:8880/v1/models'
        return AudioResult()

def test_neural_tts_requires_local_operator_header():
    with TestClient(server.app) as c:
        assert c.post('/api/voice/speak',
          json={'agent_id':'kiko','text':'Hello world'}).status_code==403

def test_neural_tts_agent_specific_audio_and_local_only(monkeypatch):
    monkeypatch.setattr(server.httpx,'AsyncClient',FakeLocalTTS)
    with TestClient(server.app) as c:
        r=c.post('/api/voice/speak',headers={'X-Exodia-Client':'exodia-dashboard'},
          json={'agent_id':'kiko','text':'Hello  world'})
        assert r.status_code==200,r.text
        assert r.content==b'ID3fake-mp3'
        assert r.headers['content-type']=='audio/mpeg'
        assert c.get('/api/voice/status').json()['available'] is True

def test_neural_tts_rejects_unknown_companion():
    with TestClient(server.app) as c:
        r=c.post('/api/voice/speak',headers={'X-Exodia-Client':'exodia-dashboard'},
          json={'agent_id':'unknown','text':'Hi'})
        assert r.status_code==422
