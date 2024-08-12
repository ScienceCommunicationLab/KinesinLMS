import logging

from django import template
from django.contrib.auth import get_user_model

from kinesinlms.external_tools.models import ExternalToolView
from kinesinlms.lti.service import ExternalToolLTIService

logger = logging.getLogger(__name__)

register = template.Library()

User = get_user_model()


@register.simple_tag(takes_context=True)
def get_external_tool_login_url(context, external_tool_view: ExternalToolView) -> str:
    """
    Builds a link to an external tool's initiation URL to start the LTI v1.3 
    OIDC process. This is often called the 'login' step.
    
    Ideally, the external tool will then redirect the user back to KinesinLMS's
    OIDC authentication URL to continue the launch process. (If that goes well,
    KinesinLMS will then send the user back to the tool using an autosubmit
    form.)
    
    """
    if not external_tool_view:
        logger.warning("get_external_tool_login_url(): external_tool_view is required.")
        return ""
    course = context.get('course', None)
    if course is None:
        logger.warning("get_external_tool_login_url(): course is required in context.")
        return ""
    user = context.get('user', None)
    if user is None:
        logger.warning("get_external_tool_login_url(): user is required in context.")
        return ""

    lti_service = ExternalToolLTIService(external_tool_view=external_tool_view,
                                     course=course)

    login_url = lti_service.get_tool_login_url(user=user)

    return login_url
