"""User-supervised browser assistance; deliberately does NOT evade anti-bot checks.

An approved host is required. Supports persistent logins and local error
screenshots; does not automatically enter prompts into paid consumer chat UIs.
"""
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone
from app.security.vault import safe_dir

class BrowserUnavailable(Exception):
    pass


def validate_url(url: str, allowed_hosts: tuple[str, ...]) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    if (parsed.scheme != 'https' or not host or parsed.username or parsed.password or
            parsed.port not in (None,443) or host not in allowed_hosts):
        raise BrowserUnavailable('Only explicitly allowlisted HTTPS hosts are permitted.')
    return url

class BrowserAssistant:
    def __init__(self, root: Path, hosts: tuple[str, ...]):
        self.root = root
        self.hosts = hosts

    async def read_page(self, url: str) -> dict:
        validate_url(url, self.hosts)
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise BrowserUnavailable('Install Playwright and its Chromium browser.') from exc
        session = self.root / 'session_data' / 'approved_browser'
        safe_dir(session)
        try:
            async with async_playwright() as play:
                context = await play.chromium.launch_persistent_context(
                    user_data_dir=str(session), headless=False)
                page = context.pages[0] if context.pages else await context.new_page()
                try:
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                    final_url = page.url
                    validate_url(final_url, self.hosts)
                    title = await page.title()
                    content = (await page.locator('body').inner_text(timeout=7000))[:6000]
                    # Do not interpret account login walls or challenge pages as content.
                    if response is not None and response.status in (403, 429, 503):
                        raise BrowserUnavailable(f'Page returned {response.status}; manual review required.')
                    return {'title':title, 'page_text':content,
                            'url':final_url, 'note':'Read-only browser-assisted snapshot. Not an LLM answer.'}
                except Exception as exc:
                    path = self.root / 'debug_snapshots'
                    safe_dir(path)
                    screenshot = path / (datetime.now(timezone.utc).strftime('dom-error-%Y%m%d-%H%M%S') + '.png')
                    try:
                        await page.screenshot(path=str(screenshot), full_page=False, timeout=5000)
                    except Exception:
                        screenshot = None
                    raise BrowserUnavailable('Browser navigation/DOM failed; screenshot saved locally: '
                                              + (screenshot.name if screenshot else 'unavailable')) from exc
                finally:
                    await context.close()
        except BrowserUnavailable:
            raise
        except Exception as exc:
            raise BrowserUnavailable('Browser could not start; install Chromium with: playwright install chromium') from exc
