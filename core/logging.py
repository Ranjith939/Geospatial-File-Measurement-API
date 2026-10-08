"""I log one JSON object per line on the "geomeasure" logger. File contents never go into the logs."""

import json
import logging

logger = logging.getLogger("geomeasure")


def log_event(event: str, level: int = logging.INFO, **fields) -> None:
    logger.log(level, json.dumps({"event": event, **fields}, default=str))
