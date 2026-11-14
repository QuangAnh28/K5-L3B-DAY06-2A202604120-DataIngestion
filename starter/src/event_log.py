"""Structured local events. Never serialize request headers, vectors or API payloads."""
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
import json
import os
import re
import uuid

RUN_ID = str(uuid.uuid4())


def redact(value):
    text = str(value)
    for key, secret in os.environ.items():
        if any(part in key.upper() for part in ('API_KEY', 'TOKEN', 'PASSWORD', 'SECRET')) and len(secret) >= 8:
            text = text.replace(secret, '[REDACTED]')
    text = re.sub(r'sk-(?:or-v1-)?[A-Za-z0-9_-]{8,}', '[REDACTED]', text)
    text = re.sub(r'(?i)Bearer\s+\S+', 'Bearer [REDACTED]', text)
    text = re.sub(r'(://[^:/\s]+:)[^@\s]+@', r'\1[REDACTED]@', text)
    return text[:1500]


def sanitize(value):
    if isinstance(value, dict):
        return {key: '[REDACTED]' if any(part in str(key).upper() for part in ('API_KEY','TOKEN','PASSWORD','SECRET'))
                else sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    return redact(value) if isinstance(value, str) else value


def record_event(stage, event, *, level='info', error=None, **context):
    path = Path(os.environ.get('LAB_LOG_PATH', Path(__file__).resolve().parents[1] / 'results/runtime_events.jsonl'))
    path.parent.mkdir(parents=True, exist_ok=True)
    row = dict(timestamp=datetime.now(timezone.utc).isoformat(), run_id=RUN_ID,
               stage=stage, event=event, level=level,
               context=sanitize(context))
    if error is not None:
        row.update(error_type=type(error).__name__, message=redact(error))
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')


@contextmanager
def operation(stage, **context):
    record_event(stage, 'started', **context)
    try:
        yield
    except Exception as exc:
        # Preserve the original failure even when the log destination is unavailable.
        try:
            record_event(stage, 'failed', level='error', error=exc, **context)
        except OSError as log_error:
            exc.add_note('Failed to write event log: ' + type(log_error).__name__)
        raise
    else:
        record_event(stage, 'completed', **context)


def logged(stage):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with operation(stage):
                return function(*args, **kwargs)
        return wrapped
    return decorate
