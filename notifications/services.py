import logging
import threading

logger = logging.getLogger(__name__)


def send_async(fn, *args, **kwargs):
    """Best-effort fire-and-forget so a slow SMTP call doesn't block the
    request. Not a replacement for a real task queue -- no retries, and a
    process restart drops anything in flight. Swap for Celery/RQ (Redis is
    already running for Channels) if guaranteed delivery ever matters.
    """
    threading.Thread(target=_safe_call, args=(fn, *args), kwargs=kwargs, daemon=True).start()


def _safe_call(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except Exception:
        logger.exception('Notification send failed: %s', getattr(fn, '__name__', fn))
