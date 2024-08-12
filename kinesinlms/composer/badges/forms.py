import logging

from django import forms
from django.utils.translation import gettext_lazy as _

from kinesinlms.badges.models import BadgeClass, BadgeClassType

logger = logging.getLogger(__name__)


class BadgeClassForm(forms.ModelForm):

    type = forms.ChoiceField(
        label=_("Accomplishment Type"),
        choices=[(BadgeClassType.COURSE_PASSED.name, BadgeClassType.COURSE_PASSED.value)],
        help_text=_("The accomplishment that will award the badge. (Only 'Passed Course' is supported at the moment.)"),
        required=True
    )

    class Meta:
        model = BadgeClass
        fields = ['type',
                  'slug',
                  'name',
                  'provider',
                  'open_badge_id',
                  'external_entity_id',
                  'image_url',
                  'description',
                  'criteria']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
