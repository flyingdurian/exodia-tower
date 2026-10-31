"""Environment-backed vault. Never expose or log secret values."""
import os
from pathlib import Path

SECRET_NAMES = {
    'OPENAI_API_KEY', 'GITHUB_TOKEN', 'ETSY_API_KEY', 'ETSY_ACCESS_TOKEN',
    'YOUTUBE_ACCESS_TOKEN', 'GMAIL_ACCESS_TOKEN'
}


def get_secret(name: str) -> str:
    if name not in SECRET_NAMES:
        raise ValueError('Secret name not allowlisted')
    return os.getenv(name, '').strip()


def safe_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        path.chmod(0o700)
    except OSError:
        pass  # Windows permissions managed separately by ACLs.


def redact(text: str) -> str:
    for name in SECRET_NAMES:
        val = os.getenv(name, '')
        if val:
            text = text.replace(val, '[REDACTED]')
    return text
