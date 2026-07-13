from django.conf import settings

import anthropic


def get_client():
    """Returns None if no API key is configured, so callers can degrade
    gracefully (503) instead of crashing on a missing key at import time.
    """
    if not settings.ANTHROPIC_API_KEY:
        return None
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
