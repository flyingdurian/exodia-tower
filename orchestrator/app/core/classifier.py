"""Deterministic, inspectable command classifier; no autonomous writes."""
import re

INTEGRATIONS = {
    'github': re.compile(r'\b(github|repo(?:sitory)?|pull request|commits?|issues?)\b', re.I),
    'etsy': re.compile(r'\b(etsy|shop|listings?|orders?|sales|inventory)\b', re.I),
    'youtube': re.compile(r'\b(youtube|channel|subscribers?|watch time|video views)\b', re.I),
    'gmail': re.compile(r'\b(gmail|inbox|unread|emails?|mail)\b', re.I),
}

def classify(prompt: str) -> tuple[str, str | None]:
    p = prompt.casefold().strip()
    if re.search(r'\b(system health|system status|connection status|integration status)\b', p):
        return 'system', None
    for name, regex in INTEGRATIONS.items():
        if regex.search(p) and re.search(r'\b(show|check|fetch|read|get|status|stats?|metrics?|overview|latest|how many|list|find)\b', p):
            return 'integration', name
    if re.search(r'\b(search|find|lookup|retrieve|indexed|knowledge base|documentation|docs)\b', p):
        return 'rag', None
    return 'reasoning', None
