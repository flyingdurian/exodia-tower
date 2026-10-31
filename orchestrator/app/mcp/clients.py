"""Read-only REST adapters for four service providers.

These are HTTP adapter seams, not full external MCP servers. An MCP protocol
server can later wrap each one; current UI labels this accurately.
"""
from datetime import date, timedelta
import os
import re
from urllib.parse import quote
import httpx
from app.security.vault import get_secret

class ServiceError(Exception):
    pass

async def _get(url: str, headers: dict, params: dict | None = None) -> dict:
    try:
        async with httpx.AsyncClient(timeout=16.0, follow_redirects=False) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code in (401, 403):
            raise ServiceError(f'Authorization failed or access denied (HTTP {code}).') from e
        if code == 429:
            raise ServiceError('Service rate limit reached (HTTP 429); retry later.') from e
        raise ServiceError(f'Service returned HTTP {code}.') from e
    except (httpx.RequestError, ValueError) as e:
        raise ServiceError(f'Service unavailable or invalid response: {type(e).__name__}.') from e

async def github_overview() -> dict:
    repo = os.getenv('GITHUB_REPO','').strip()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ServiceError('Set GITHUB_REPO=owner/name in .env.')
    token = get_secret('GITHUB_TOKEN')
    if not token:
        raise ServiceError('Set GITHUB_TOKEN in .env.')
    headers = {'Authorization': f'Bearer {token}', 'Accept':'application/vnd.github+json',
               'X-GitHub-Api-Version':'2022-11-28'}
    data = await _get(f'https://api.github.com/repos/{repo}', headers)
    return {'repository': data.get('full_name'), 'description':data.get('description'),
            'default_branch':data.get('default_branch'), 'open_issues_count':data.get('open_issues_count'),
            'stars':data.get('stargazers_count'), 'last_push':data.get('pushed_at'),
            'url':data.get('html_url'), 'note':'GitHub open_issues_count includes pull requests.'}

async def etsy_overview() -> dict:
    key = get_secret('ETSY_API_KEY')
    token = get_secret('ETSY_ACCESS_TOKEN')
    shop_id = os.getenv('ETSY_SHOP_ID','').strip()
    if not key or not token or not shop_id.isdigit():
        raise ServiceError('Set ETSY_API_KEY, ETSY_ACCESS_TOKEN and numeric ETSY_SHOP_ID.')
    headers = {'x-api-key':key, 'Authorization': f'Bearer {token}'}
    data = await _get(f'https://api.etsy.com/v3/application/shops/{shop_id}', headers)
    return {'shop_name':data.get('shop_name'), 'shop_id':data.get('shop_id'),
            'listing_active_count':data.get('listing_active_count'),
            'transaction_sold_count':data.get('transaction_sold_count'),
            'currency_code':data.get('currency_code'),
            'url':data.get('url'), 'note':'Shop-level counts only; revenue reporting needs a separate approved report and scopes.'}

async def youtube_overview() -> dict:
    token = get_secret('YOUTUBE_ACCESS_TOKEN')
    if not token:
        raise ServiceError('Set YOUTUBE_ACCESS_TOKEN (OAuth access token with Analytics scope).')
    end_date = date.today() - timedelta(days=2)  # reporting may lag
    start_date = end_date - timedelta(days=27)
    data = await _get('https://youtubeanalytics.googleapis.com/v2/reports',
                      {'Authorization': f'Bearer {token}'},
                      {'ids':'channel==MINE', 'startDate':start_date.isoformat(),
                       'endDate':end_date.isoformat(), 'metrics':'views,estimatedMinutesWatched,subscribersGained',
                       'dimensions':'day', 'sort':'day'})
    headers = [c.get('name') for c in data.get('columnHeaders', [])]
    totals = {'views':0, 'estimatedMinutesWatched':0, 'subscribersGained':0}
    for row in data.get('rows',[]):
        for i, key in enumerate(headers):
            if key in totals and i < len(row):
                totals[key] += row[i]
    return {'period_start':start_date.isoformat(), 'period_end':end_date.isoformat(),
            'views':totals['views'], 'watch_time_hours':round(totals['estimatedMinutesWatched']/60, 1),
            'subscribers_gained':totals['subscribersGained'],
            'note':'Estimated report for the selected 28-day period, not a live counter.'}

async def gmail_overview() -> dict:
    token = get_secret('GMAIL_ACCESS_TOKEN')
    if not token:
        raise ServiceError('Set GMAIL_ACCESS_TOKEN (OAuth access token with gmail.readonly).')
    headers = {'Authorization':f'Bearer {token}'}
    result = await _get('https://gmail.googleapis.com/gmail/v1/users/me/messages',
                        headers, {'q':'is:unread', 'maxResults':10})
    ids = [m.get('id') for m in result.get('messages', []) if m.get('id')]
    return {'unread_estimate':result.get('resultSizeEstimate',0),
            'sample_message_ids':ids, 'note':'Estimated unread count; message bodies are not fetched or indexed.'}

SERVICES = {'github':github_overview, 'etsy':etsy_overview,
            'youtube':youtube_overview, 'gmail':gmail_overview}

async def service_overview(name: str) -> dict:
    if name not in SERVICES:
        raise ServiceError('Unknown integration')
    return await SERVICES[name]()
