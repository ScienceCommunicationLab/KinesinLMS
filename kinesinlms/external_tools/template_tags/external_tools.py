import logging

from django import template
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

register = template.Library()

User = get_user_model()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# SIMPLE TAGS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
