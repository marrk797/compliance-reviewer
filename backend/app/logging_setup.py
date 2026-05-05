"""Logging configuration with redaction of document contents and prompts.

Privacy rules enforced here:

* Any log record carrying ``extra={"contains_document": True}`` (or with the
  attribute ``contains_document=True``) is dropped entirely.
* Any record where the message body would otherwise expose user document text
  must be tagged with that flag by the caller. As a defence in depth, large
  string payloads are also truncated.
"""
from __future__ import annotations

import logging
import sys

from app.config import settings


class DocumentContentFilter(logging.Filter):
    """Drop records that the caller marked as containing user content."""

    MAX_MESSAGE_LEN = 2000

    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "contains_document", False):
            return False
        if getattr(record, "contains_prompt", False):
            return False
        msg = record.getMessage()
        if len(msg) > self.MAX_MESSAGE_LEN:
            record.msg = msg[: self.MAX_MESSAGE_LEN] + "...[truncated]"
            record.args = ()
        return True


def configure_logging() -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    handler.addFilter(DocumentContentFilter())
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())
