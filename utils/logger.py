"""IngreLens AI — Centralized logging setup."""
import logging
import sys
from config.settings import settings

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        # stderr, not stdout: mcp_server.py's stdio transport uses stdout as
        # the JSON-RPC message channel — any log line written there corrupts
        # the protocol (confirmed: ADK's McpToolset failed to parse a log
        # line as a JSON-RPC message before this fix). stderr is also just
        # the conventional place for application logs to begin with.
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(settings.LOG_FORMAT))
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))
    return logger
