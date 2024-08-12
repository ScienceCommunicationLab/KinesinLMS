import logging

import factory

from kinesinlms.custom_app.models import CustomApp

logger = logging.getLogger(__name__)


class CustomAppFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomApp
