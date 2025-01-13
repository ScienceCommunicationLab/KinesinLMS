import factory  # noqa
from kinesinlms.external_tools.models import ExternalToolProvider, ExternalToolView
from kinesinlms.external_tools.constants import ExternalToolProviderType


class ExternalToolProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExternalToolProvider

    name = "Test provider"
    description = "This is a test provider"
    type = ExternalToolProviderType.BASIC_LTI13.name
    slug = "test-provider"
    login_url = "https://example.com/oidc/login"
    launch_uri = "https://example.com/launch"
    active = True
    client_id = "client-id-1"


class ExternalToolViewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExternalToolView
