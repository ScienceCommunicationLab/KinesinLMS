from enum import Enum
import logging
from typing import Optional

from django.contrib.sites.models import Site
from django.db import models
from django.utils.translation import gettext_lazy as _
from slugify import slugify

from kinesinlms.core.fields import AutoCharField
from kinesinlms.core.models import Trackable
from kinesinlms.core.utils import get_domain
from kinesinlms.external_tools.constants import (
    ExternalToolViewLaunchType,
    LTIVersionType,
    ExternalToolProviderType,
    ConnectionMethodType,
)
from kinesinlms.learning_library.models import Block

logger = logging.getLogger(__name__)


class UsernameField(Enum):
    """
    The field in the user model that will be used to identify the user.
    """

    USERNAME = "username"
    EMAIL = "email"
    ANON_USERNAME = "anonymous username"


class ExternalToolProvider(Trackable):
    """
    External tool provider, connected by LTI v1.3.
    At the moment the only type of tool we support is a JupyterHub service.
    """

    name = models.CharField(
        max_length=200,
        unique=True,
        null=False,
        blank=False,
        help_text=_("Name of external tool."),
    )

    description = models.TextField(
        null=True, blank=True, help_text=_("Description of external tool.")
    )

    lti_version = models.CharField(
        max_length=100,
        choices=[(tag.name, tag.value) for tag in LTIVersionType],
        default=LTIVersionType.LTI_1_3.name,
        null=False,
        blank=False,
    )

    type = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in ExternalToolProviderType],
        default=ExternalToolProviderType.JUPYTER_HUB.name,
        null=False,
        blank=False,
    )

    connection_method = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in ConnectionMethodType],
        default=ConnectionMethodType.MANUAL.name,
        null=False,
        blank=False,
    )

    username_field = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in UsernameField],
        default=UsernameField.USERNAME.name,
        null=False,
        blank=False,
        help_text=_(
            "The field in the user model that will be used to identify the user to the tool"
        ),
    )

    slug = models.SlugField(
        max_length=200,
        unique=True,
        null=False,
        blank=False,
        help_text=_(
            "Slug identifier for provider " "(used in e.g. course json imports)."
        ),
    )

    login_url = models.URLField(
        null=True,
        blank=True,
        help_text=_(
            "The login URL that starts the "
            "OpenID Connect process for this external tool. "
            "Sometimes this URL is called the 'initiate login', the 'OIDC url' or just 'login' url. "
            "This field can be left empty if not required by external tool."
        ),
    )

    launch_uri = models.URLField(
        null=False,
        blank=False,
        help_text=_(
            "The launch (target link) URI for this external tool."
            "This is the URL to launch the tool once the login process is complete."
            "Sometimes this URL is called the 'redirection URI'."
        ),
    )

    active = models.BooleanField(
        default=False,
        blank=False,
        null=False,
        help_text=_("Enable external tool provider."),
    )

    # TODO:
    #   Is it that *either* public_keyset_url *or* public_key
    #   is required for LTI Advantage?

    public_keyset_url = models.URLField(
        null=True,
        blank=True,
        help_text="The public keyset URL for the external tool. "
        "The public key for the external tool. "
        "(Only needed if you want to support LTI Advantage.)",
    )

    public_key = models.TextField(
        null=True,
        blank=True,
        help_text=_(
            "The public key for the external tool. "
            "(Only needed if you want to support LTI Advantage.)"
        ),
    )

    client_id = models.SlugField(
        null=True,
        blank=True,
        help_text=_(
            "The opaque client ID that represents the tool in KinesinLMS. "
            "This will be provided to the tool as part of the LTI configuration."
        ),
    )

    def __str__(self):
        return f"{self.name} [type: {self.type}]"

    # --------------------------------------------------
    # MODEL PROPERTIES
    # --------------------------------------------------

    @property
    def issuer(self) -> str:
        """
        For now, the issuer is just our root domain
        """
        domain = get_domain()
        url = f"https://{domain}/"
        return url

    @property
    def deployment_id(self) -> str:
        """
        Not supporting multi-tenancy at the moment, so just return the site ID.
        """
        try:
            site_id = Site.objects.get_current().id
        except Exception:
            logger.error("Could not get current site ID.")
            site_id = 1

        return str(site_id)

    # --------------------------------------------------
    # METHODS
    # --------------------------------------------------

    def get_sub(self, user) -> str:
        """
        The 'subject' of the token based on this model's settings.
        """
        if self.username_field == UsernameField.USERNAME.name:
            return user.username
        elif self.username_field == UsernameField.EMAIL.name:
            return user.email
        elif self.username_field == UsernameField.ANON_USERNAME.name:
            return user.anon_username
        else:
            raise ValueError(f"Unknown username_field: {self.username_field}")

    def save(self, *args, **kwargs):
        if not self.slug:
            slug = slugify(self.name)
            if len(slug) > 100:
                slug = slug[:100]
            self.slug = slug

        if not self.client_id:
            self._create_client_id()

        super().save(*args, **kwargs)

    def _create_client_id(self):
        if not self.client_id:
            max_client_id = (
                ExternalToolProvider.objects.all().aggregate(models.Max("client_id"))[
                    "client_id__max"
                ]
                or 9999
            )
            self.client_id = max_client_id + 1


class ExternalToolView(Trackable):
    """
    External tool view, connected by LTI v1.3.

    Provides configuration information for a particular view (document, assessment, lesson, etc.)
    of a resource in external tool.

    This is associated directly with a block in a CourseUnit.

    NOTE:
        Wasn't sure what to call all the things that might be made available via LTI provider
        (document, assessment, lesson, etc.) so I just called it a 'view'.

    """

    external_tool_provider = models.ForeignKey(
        ExternalToolProvider,
        on_delete=models.CASCADE,
        related_name="external_tool_views",
        null=True,
        blank=True,
    )

    block = models.OneToOneField(
        Block, on_delete=models.CASCADE, related_name="external_tool_view"
    )

    launch_type = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in ExternalToolViewLaunchType],
        default=ExternalToolViewLaunchType.IFRAME.name,
        null=False,
        blank=False,
    )

    # Per the LTI 1.3 standard:
    #
    #           Each LTI Link connected to a particular resource
    #           MUST contain a platform unique identifier named resource_link_id.
    #
    # ...and in another spot the standard describes the rational for this id:
    #
    #           LTI uses the resource_link_id property to help platforms and tools differentiate
    #           amongst multiple links embedded in a single context. While all the links within a
    #           context will share the same context_id, each LTI resource link will have a platform
    #           wide unique resource link ID.
    #
    # So essentially anytime we have a button saying "Launch External Tool"
    # we need to have a globally unique identifier for that link.
    #
    # We use the uuid attached to this model instance as part of that unique identifier
    # Use our own AutoCharField to generate the unique uuid identifier.
    resource_link_id = AutoCharField(
        unique=True,
        blank=False,
        editable=True,
        help_text=_("A unique identifier for this external tool view."),
    )

    custom_target_link_uri = models.CharField(
        verbose_name=_("Custom Target Link URI"),
        null=True,
        blank=True,
        max_length=1000,
        help_text=_(
            "A custom target link helps direct to a particular resources in the external tool. If this URL is not defined, the default launch URI of the ExternalToolProvider will be used to launch the tool."
        ),
    )

    append_to_default_launch_uri = models.BooleanField(
        verbose_name=_("Append custom target link URI to default launch URI"),
        default=False,
        blank=False,
        help_text=_(
            "If True, the 'Custom Target Link URI' will be appended to the default launch URI to create "
            "a full URL for the 'target_link_uri' sent to the tool when launched."
            "If False, the 'Custom Target Link URI' will be used as the full URL in the 'target_link_uri'."
        ),
    )

    @property
    def target_link_uri(self) -> Optional[str]:
        """
        The target link URI for this external tool view. This is the URL that will
        launch (once the login process is complete) a specific view of the tool for
        this particular point in the course. So this URL might be a very specific path
        to a particular resource in the tool.

        If the ExternalToolView does not define a custom launch URI, then we will
        use the launch URI of the ExternalToolProvider.

        Returns:
            Optional[str]: _description_
        """

        if not self.external_tool_provider:
            logger.error(
                f"Cannot determine launch URL. ExternalToolView '{self}' does "
                f"not have an ExternalToolProvider"
            )
            return None

        default_launch_uri = self.external_tool_provider.launch_uri
        if not default_launch_uri:
            logger.error(
                f"Cannot determine launch URL. ExternalToolProvider '{self.external_tool_provider}' "
                f"does not have a launch URI defined"
            )
            return None

        if self.custom_target_link_uri:
            if self.append_to_default_launch_uri:
                return f"{default_launch_uri}{self.custom_target_link_uri}"
            else:
                return self.custom_target_link_uri

        return default_launch_uri

    @property
    def launch_uri(self) -> str:
        """
        The launch URI for this external tool view.
        """
        if self.external_tool_provider:
            return self.external_tool_provider.launch_uri
        return ""
