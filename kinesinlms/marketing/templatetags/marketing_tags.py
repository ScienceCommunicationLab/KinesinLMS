import logging
from typing import List

from django import template
import waffle

from kinesinlms.core.constants import SiteFeatures
from kinesinlms.marketing.models import Testimonial

logger = logging.getLogger(__name__)

register = template.Library()


@register.simple_tag()
def home_page_testimonials() -> List[Testimonial]:
    """
    Get testimonials to show on the front page.
    Don't return any if the site isn't configured
    to show testimonials, and only return Testimonials
    that aren't related to a course.

    Limits to 10.

    Returns:
        A list of Testimonial objects
    """
    try:
        if waffle.switch_is_active(SiteFeatures.TESTIMONIALS.name):
            return []
        testimonials = Testimonial.objects.filter(course__isnull=True)[:10]
        return testimonials
    except Exception:
        logger.exception("Error getting testimonials")
        return []
