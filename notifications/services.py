import logging

logger = logging.getLogger(__name__)


def send_async(fn, *args, **kwargs):
    """Persist delivery before returning; run_worker processes jobs with retries."""
    from workspace_tools.services import enqueue
    task = args[0]
    kinds = {'send_task_assigned_email': 'task_assigned', 'send_due_date_reminder_email': 'task_reminder'}
    if fn.__name__ not in kinds:
        raise ValueError('Unsupported notification handler.')
    assigned_by = kwargs.get('assigned_by')
    return enqueue(kinds[fn.__name__], {'task': task.pk, 'assignee': task.assigned_to_id,
                                       'assigned_by': assigned_by.pk if assigned_by else None})


def _safe_call(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except Exception:
        logger.exception('Notification send failed: %s', getattr(fn, '__name__', fn))
