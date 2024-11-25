import logging
from typing import Optional

from django import template
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site
from django.template import Context, Template
from django.utils.safestring import mark_safe
from markdownify.templatetags.markdownify import markdownify

from config.settings.base import ACCEPT_ANALYTICS_COOKIE_NAME
from kinesinlms.course.models import CourseUnit
from kinesinlms.learning_library.constants import ContentFormatType
from kinesinlms.learning_library.models import Block, Resource, ResourceType
from kinesinlms.survey.models import SurveyProvider

logger = logging.getLogger(__name__)

register = template.Library()

User = get_user_model()


# FILTERS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~


@register.filter
def show_none_for_none(value):
    """Our own variation on Django's default_if_none."""
    if value is None:
        return mark_safe("<span class='text-body-tertiary'>( none )</span>")
    return value


# SIMPLE TAGS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~


@register.simple_tag
def get_jupyter_notebook_resource(block) -> Optional[Resource]:
    """
    Get the Jupyter notebook resource for a block, if it exists.
    """
    if block:
        jupyter_notebook = block.resources.filter(
            type=ResourceType.JUPYTER_NOTEBOOK.name
        ).first()
        return jupyter_notebook
    return None


@register.simple_tag(takes_context=True)
def is_analytics_cookies_accepted(context):
    request = getattr(context, "request", None)
    if request:
        try:
            cookie_value = request.COOKIES.get(ACCEPT_ANALYTICS_COOKIE_NAME, None)
            return cookie_value == "ACCEPT"
        except Exception:
            logger.exception("Could not get COOKIES value")
            return False
    else:
        return False


@register.simple_tag
def site_url() -> str:
    current_site = Site.objects.get_current()
    url = f"https://{current_site.domain}"
    return url


@register.simple_tag
def site_domain() -> str:
    current_site = Site.objects.get_current()
    return current_site.domain


@register.simple_tag(takes_context=True)
def site_name(context) -> Optional[str]:
    request = context.get("request", None)
    if request:
        site = get_current_site(request)
        if site.name:
            return site.name
        else:
            return "(no site name defined)"
    else:
        logger.exception("site is not defined.")
    return None


@register.simple_tag()
def newsletter_signup_url():
    site = Site.objects.get_current()
    site_profile = getattr(site, "profile", None)
    if site_profile and site_profile.newsletter_signup_url:
        return site_profile.newsletter_signup_url
    return None


@register.simple_tag()
def educators_newsletter_signup_url():
    site = Site.objects.get_current()
    site_profile = getattr(site, "profile", None)
    if site_profile and site_profile.educators_newsletter_signup_url:
        return site_profile.educators_newsletter_signup_url
    return None


@register.simple_tag()
def facebook_page_url() -> Optional[str]:
    site = Site.objects.get_current()
    site_profile = getattr(site, "profile", None)
    if site_profile and site_profile.facebook_url:
        return site_profile.facebook_url
    return None


@register.simple_tag()
def twitter_username() -> Optional[str]:
    site = Site.objects.get_current()
    site_profile = getattr(site, "profile", None)
    if site_profile and site_profile.twitter_username:
        return site_profile.twitter_username
    return None


@register.simple_tag()
def twitter_page_url() -> Optional[str]:
    site = Site.objects.get_current()
    site_profile = getattr(site, "profile", None)
    if site_profile:
        username = site_profile.twitter_username
        if username:
            return f"https://twitter.com/{username}"
    return None


@register.simple_tag()
def google_analytics_id() -> Optional[str]:
    if settings.GOOGLE_ANALYTICS_ID:
        return settings.GOOGLE_ANALYTICS_ID
    return None


@register.simple_tag()
def support_email() -> Optional[str]:
    """
    User might have specific email for support, to provide that first.
    Otherwise, return the basic contact email, if available.
    """
    try:
        site = Site.objects.get_current()
        site_profile = getattr(site, "profile", None)
        if site_profile and site_profile.support_email:
            return site_profile.support_email
    except Exception as e:
        logger.exception(f"Could not get support_email from site profile: {e}")

    if hasattr(settings, "CONTACT_EMAIL"):
        return settings.CONTACT_EMAIL
    else:
        logger.warning(
            "No support email is defined for this site, and CONTACT_EMAIL is not defined in settings."
        )
        return None


@register.simple_tag
def settings_value(name):
    return getattr(settings, name, "")


@register.simple_tag
def url_replace(request, field, value):
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()


@register.simple_tag
def analytics_cookie_value(request) -> Optional[str]:
    """
    Returns a list of cookie groups that have not been accepted or declined.
    """

    if not request:
        return None

    try:
        accept_analytics_cookie_val = request.COOKIES.get(
            ACCEPT_ANALYTICS_COOKIE_NAME, None
        )
    except Exception as e:
        logger.exception(f"Could not get COOKIES from request: {e}")
        return None

    if not accept_analytics_cookie_val:
        return None
    if accept_analytics_cookie_val not in ["ACCEPT", "REJECT"]:
        logger.exception(
            f"analytics_cookie_value(): cookie value is not ACCEPT or REJECT."
            f"value : {accept_analytics_cookie_val}"
        )
        return "REJECT"
    return accept_analytics_cookie_val


@register.simple_tag
def block_resource_url(image_name: str) -> str:
    """
    Give the full URL for a Resource object that is stored as a block resource,
    given only the image name.
    """
    url = f"{settings.MEDIA_URL}block_resources/{image_name}"
    return url


@register.simple_tag
def get_badge_provider_enabled():
    current_site = Site.objects.get_current()
    enabled = (
        hasattr(current_site, "badge_provider") and current_site.badge_provider.active
    )
    return enabled


@register.simple_tag
def get_email_automation_provider_enabled():
    current_site = Site.objects.get_current()
    enabled = (
        hasattr(current_site, "email_automation_provider")
        and current_site.email_automation_provider.active
    )
    return enabled


@register.simple_tag
def get_forum_provider_enabled():
    current_site = Site.objects.get_current()
    enabled = (
        hasattr(current_site, "forum_provider") and current_site.forum_provider.active
    )
    return enabled


@register.simple_tag
def get_survey_provider_enabled():
    enabled = SurveyProvider.objects.filter(active=True).exists()
    return enabled


@register.simple_tag(takes_context=True)
def render_html_content(context, item: Block | CourseUnit) -> str:
    """
    Render content stored in a Block or CourseUnit's html_content
    field to actual HTML, if the content type is HTML.

    Args:
        context:
        item:

    Returns:
        str
    """

    if not item:
        return ""
    html_content = getattr(item, "html_content", None)
    if not html_content:
        return ""

    if item.html_content_type == ContentFormatType.HTML.name:
        if item.enable_template_tags:
            # Make sure we load any tag libraries that will be used
            # by Django template tags allowed in html_content.
            html_content = (
                "{% load core_tags unit_extras static %}\n" + item.html_content
            )

            template = Template(html_content)

            # Create a Context object with the provided context_data
            context = Context(context)

            # Render the template with the given context
            rendered_html = template.render(context)
        else:
            rendered_html = html_content

    elif item.html_content_type == ContentFormatType.MARKDOWN.name:
        # Convert markdown to HTML
        rendered_html = markdownify(item.html_content)
    else:
        # Return plain text (not marked safe).
        return item.html_content

    return mark_safe(rendered_html)
