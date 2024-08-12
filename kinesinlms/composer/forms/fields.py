import logging

from django import forms
from django.core.exceptions import ValidationError

from kinesinlms.learning_library.models import LearningObjective
from kinesinlms.speakers.models import Speaker

logger = logging.getLogger(__name__)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Custom Form Fields and helper methods
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SpeakersField(forms.CharField):

    def __init__(self, *args, **kwargs):
        super(SpeakersField, self).__init__(*args, **kwargs)
        self.help_text = "Speakers, identified by slugs (e.g. alexandra-schnoes), with slugs separated by commas"
        self.max_length = 300
        self.required = False

    def clean(self, value):
        if value:
            speaker_slugs = value.split(",")
            speaker_slugs = [item.strip() for item in speaker_slugs]
            for speaker_slug in speaker_slugs:
                try:
                    Speaker.objects.get(slug=speaker_slug)
                except LearningObjective.DoesNotExist:
                    raise ValidationError(f"Speaker with slug {speaker_slug} does not exist")
        return value


class LearningObjectivesField(forms.CharField):

    def __init__(self, *args, **kwargs):
        super(LearningObjectivesField, self).__init__(*args, **kwargs)
        self.help_text = "Learning objective IDS, separated by commas"
        self.max_length = 300
        self.required = False

    def clean(self, value):
        if value:
            lo_slugs = value.split(",")
            lo_slugs = [item.strip() for item in lo_slugs]
            for lo_slug in lo_slugs:
                try:
                    LearningObjective.objects.get(slug=lo_slug)
                except LearningObjective.DoesNotExist:
                    raise ValidationError(f"Learning Objective with slug {lo_slug} does not exist")
        return value
