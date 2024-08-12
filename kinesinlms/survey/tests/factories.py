import logging

import factory

from kinesinlms.survey.models import Survey, SurveyEmail, SurveyProvider, SurveyProviderType

logger = logging.getLogger(__name__)


class SurveyProviderFactory(factory.django.DjangoModelFactory):
    name = "Some qualtrics account"
    type = SurveyProviderType.QUALTRICS.name
    slug = "qualtrics-kinesinlms"
    datacenter_id = "iad1"

    class Meta:
        model = SurveyProvider


class SurveyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Survey


class SurveyEmailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SurveyEmail
