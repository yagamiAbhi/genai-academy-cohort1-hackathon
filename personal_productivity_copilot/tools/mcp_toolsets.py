from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

from ..config import CALENDAR_MCP_URL, TASK_MCP_URL, NOTES_MCP_URL


def build_calendar_toolset():
    if not CALENDAR_MCP_URL:
        raise ValueError("CALENDAR_MCP_URL is not set")

    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=CALENDAR_MCP_URL,
            headers={},
        ),
    )


def build_task_toolset():
    if not TASK_MCP_URL:
        raise ValueError("TASK_MCP_URL is not set")

    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=TASK_MCP_URL,
            headers={},
        ),
    )


def build_notes_toolset():
    if not NOTES_MCP_URL:
        raise ValueError("NOTES_MCP_URL is not set")

    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=NOTES_MCP_URL,
            headers={},
        ),
    )