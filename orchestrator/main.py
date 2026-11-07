"""Main entrypoint: python main.py"""
from app.config import Settings
import uvicorn

if __name__ == '__main__':
    conf = Settings()
    if conf.host not in ('127.0.0.1','localhost'):
        raise SystemExit('Public binding is blocked in this prototype; configure authentication first.')
    print(f'Exodia Tower ready: http://{conf.host}:{conf.port}')
    uvicorn.run('app.api.server:app', host=conf.host, port=conf.port, reload=False)
