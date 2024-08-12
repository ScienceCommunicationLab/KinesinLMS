"""
Models for institutions module.
"""
import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import CharField, SlugField
from django.utils.translation import gettext_lazy as _
from mptt.models import MPTTModel

from kinesinlms.core.models import Trackable

logger = logging.getLogger(__name__)

User = get_user_model()


class Institution(Trackable):
    """
    Models institutions that students may be associated with
    via a Cohort.
    """

    slug = SlugField(max_length=250,
                     blank=True,
                     null=True,
                     help_text=_('Slug for institution'))

    name = CharField(blank=True,
                     null=True,
                     max_length=200,
                     help_text=_("The name of this Institution"))

    def __str__(self):
        return self.name
