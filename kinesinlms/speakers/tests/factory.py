from django.utils.timezone import now
# noinspection PyUnresolvedReferences
from factory.django import DjangoModelFactory

from kinesinlms.speakers.models import Speaker


class SpeakerFactory(DjangoModelFactory):
    first_name = "Tracy"
    last_name = "McTestSpeaker"
    video_url = "example.com/video/12345"
    institution = "Test Institution"
    bio = "Tracy is an accomplished professor."
    created_at = now()
    updated_at = now()
    suffix = "PhD"
    full_name = "Tracy McTestSpeaker"

    class Meta:
        model = Speaker
        django_get_or_create = ('slug',)
