"""Optional, read-only MCP stdio tool server (SDK 2.x).

Install requirements-mcp.txt and run: python -m app.mcp.server
An MCP-compatible client starts this as a process over stdio.
"""
from mcp.server import MCPServer
from app.mcp.clients import service_overview, ServiceError
from app.rag.engine import CrystalArchives
from app.config import Settings, enabled

mcp = MCPServer('Command Tower · Relic Inventory')

@mcp.tool()
async def github_repo_overview() -> dict:
    """Read configured GitHub repository metadata. No writes."""
    try:
        return await service_overview('github')
    except ServiceError as exc:
        return {'error':str(exc)}

@mcp.tool()
async def etsy_shop_overview() -> dict:
    """Read configured Etsy seller shop metadata. No writes."""
    try:
        return await service_overview('etsy')
    except ServiceError as exc:
        return {'error':str(exc)}

@mcp.tool()
async def youtube_channel_report() -> dict:
    """Read the authenticated YouTube channel's recent analytics. No writes."""
    try:
        return await service_overview('youtube')
    except ServiceError as exc:
        return {'error':str(exc)}

@mcp.tool()
async def gmail_inbox_pulse() -> dict:
    """Read estimated unread message count without message bodies. No writes."""
    try:
        return await service_overview('gmail')
    except ServiceError as exc:
        return {'error':str(exc)}

@mcp.tool()
def search_local_archives(query: str) -> list[dict]:
    """Search the operator's indexed local workspace for relevant snippets."""
    settings=Settings()
    archives=CrystalArchives(settings.database, settings.index_root, dense=enabled('DENSE_SEARCH'))
    return archives.search(query,limit=5)

if __name__=='__main__':
    mcp.run(transport='stdio')
