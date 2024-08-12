from django.conf import settings


def settings_context(_request):
    """Settings available by default to the templates context."""
    # Note: we intentionally do NOT expose the entire settings
    # to prevent accidental leaking of sensitive information
    context_settings = {
        "DEBUG": settings.DEBUG,
        "KINESINLMS_JAVASCRIPT_VERSION": settings.KINESINLMS_JAVASCRIPT_VERSION
    }
    return context_settings
