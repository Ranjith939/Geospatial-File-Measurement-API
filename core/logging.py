"""Structured logs: one JSON object per line on the "geomeasure" logger, never file contents."""

import json
import logging

logger = logging.getLogger("geomeasure")


def log_event(event: str, level: int = logging.INFO, **fields) -> None:
    logger.log(level, json.dumps({"event": event, **fields}, default=str))
