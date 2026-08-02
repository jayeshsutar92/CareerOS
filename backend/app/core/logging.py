import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key in (
            "method",
            "path",
            "status_code",
            "duration_ms",
            "ai_provider",
            "ai_model",
            "ai_request_id",
            "ai_prompt_tokens",
            "ai_completion_tokens",
            "ai_total_tokens",
            "ai_total_cost",
            "agent_name",
            "agent_run_id",
            "agent_status",
            "agent_attempt",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        return json.dumps(payload, default=str)


def configure_logging(log_level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())

    logging.getLogger("uvicorn.access").handlers.clear()
