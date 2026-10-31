"""Configuration and local-only security boundaries."""
from dataclasses import dataclass
from pathlib import Path
import os
import shutil

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env', override=False)


def enabled(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    host: str = os.getenv('HOST', '127.0.0.1')
    port: int = int(os.getenv('PORT', '8765'))
    openai_model: str = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
    browser_enabled: bool = enabled('BROWSER_ENABLED')
    allowed_hosts: tuple[str, ...] = tuple(h.strip().lower() for h in os.getenv('BROWSER_ALLOWED_HOSTS', '').split(',') if h.strip())
    browser_read_url: str = os.getenv('BROWSER_READ_URL', '')

    @property
    def index_root(self) -> Path:
        return (self.root / os.getenv('INDEX_ROOT', '.')).resolve()

    @property
    def database(self) -> Path:
        target = self.root / 'app_data' / 'exodia_tower.sqlite'
        legacy = self.root / 'app_data' / 'command_tower.sqlite'
        if not target.exists() and legacy.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy, target)  # preserve historic archive/cache intact
        return target

    def public_config(self) -> dict:
        return {
            'integrations': {key: bool(os.getenv(secret)) for key, secret in {
                'github': 'GITHUB_TOKEN', 'etsy': 'ETSY_ACCESS_TOKEN',
                'youtube': 'YOUTUBE_ACCESS_TOKEN', 'gmail': 'GMAIL_ACCESS_TOKEN'
            }.items()},
            'llm': bool(os.getenv('OPENAI_API_KEY')),
            'model': self.openai_model if os.getenv('OPENAI_API_KEY') else None,
            'browser_enabled': self.browser_enabled,
            'browser_host_count': len(self.allowed_hosts),
            'mode': 'local prototype',
        }
