from typing import Tuple
from urllib.parse import urlencode

from dataclasses import asdict
from django.conf import settings
from django.contrib.auth import get_user_model
import logging

from kinesinlms.core.utils import get_current_site_profile
from kinesinlms.core.models import SiteProfile
from kinesinlms.course.models import Course
from kinesinlms.external_tools.constants import LTI1P3InstitutionCoreRoles
from kinesinlms.external_tools.models import ExternalToolView, ExternalToolProvider
from kinesinlms.learning_library.models import Block
from kinesinlms.lti.models import (
    ExternalToolLaunchData,
    LTI1v3ClaimsData,
    LTIToolLoginData,
    ToolAuthRequestData,
    LTIParamName,
    LTIContextType,
)

User = get_user_model()

logger = logging.getLogger(__name__)


class ExternalToolLTIService:
    """
    A service class that manages the operations of KinesinLMS as an LTI "platform"
    as it interacts with an external tool.

    This class handles the LTI OIDC login process with an external tool and the
    'launch' of the tool once the login is complete.

    A reminder on terminology in LTIv1.3 (because it seems to have shifted over time):
        - a "platform" is the LMS that hosts an external tool. In this case, KinesinLMS.
        - a "tool" is the external tool that will be shown within the platform after the
          OIDC connection is made

    """

    external_tool_view: ExternalToolView = None
    external_tool_provider: ExternalToolProvider = None

    course: Course = None

    def __init__(
        self,
        external_tool_view: ExternalToolView,
        course: Course,
    ):
        """
        Init the service and check for prereqs.

        Most importantly, this class expects that a django-oauth-toolkit
        Application has been set up a linked to the ExternalToolProvider.

        Args:
            external_tool_view: The ExternalToolView object that represents the
                external tool that we're connecting to in the context of a course.
            course: The course that the user is interacting with.

        """
        if not external_tool_view:
            raise ValueError("external_tool_view is required.")
        if not external_tool_view.external_tool_provider:
            raise ValueError(
                "external_tool_view does not have an" "external_tool_provider defined."
            )

        if not course:
            raise ValueError("course is required.")

        self.external_tool_view: ExternalToolView = external_tool_view
        self.external_tool_provider: ExternalToolProvider = (
            external_tool_view.external_tool_provider
        )
        self.course: Course = course

    # --------------------------------------------------
    # PROPERTIES
    # --------------------------------------------------

    @property
    def public_key(self) -> str:
        return settings.LTI_PLATFORM_PUBLIC_KEY

    # --------------------------------------------------
    # METHODS
    # --------------------------------------------------

    def get_tool_login_url(self, user: User) -> str:
        """
        Get a login URL to start the login process on the external tool.
        This is the first step in the LTIv1.3 "third party initiated flow"
        OIDC login process.
        """

        login_hint = self.get_login_hint(user=user)

        if not hasattr(self.external_tool_view, "external_tool_provider"):
            raise Exception("ExternalToolView does not have an ExternalToolProvider.")

        etp: ExternalToolProvider = self.external_tool_provider
        if not etp.login_url:
            raise Exception("ExternalToolProvider does not have a login URL.")
        if not etp.launch_uri:
            raise Exception("ExternalToolProvider does not have a launch URI.")

        base_login_url = etp.login_url

        # Add expected OIDC login parameters for LTIv1.3
        # (See LTIToolLoginData for descriptions of fields.)
        login_data = LTIToolLoginData(
            iss=etp.issuer,
            lti_deployment_id=etp.deployment_id,
            client_id=etp.client_id,
            login_hint=login_hint,
            target_link_uri=etp.launch_uri,
            lti_message_hint=login_hint,
        )
        params_encoded = urlencode(login_data.params)
        login_url = f"{base_login_url}?{params_encoded}"

        return login_url

    def get_login_hint(self, user: User) -> str:
        """
        The 'login hint' required by the LTIv1.3 process.
        This is an internal (for us) identifier for the user and the external tool as
        it appears in the user's current interaction.
        """

        # We include course, user and block information in the hint.

        return f"c_{self.course.id}_b_{self.external_tool_view.block.id}_u_{user.anon_username}"

    @staticmethod
    def deconstruct_login_hint(
        login_hint: str,
    ) -> Tuple[Course, ExternalToolView, User]:
        """
        Deconstruct the login hint into its parts.
        """
        try:
            parts = login_hint.split("_u_")
            user_anon_username = parts[1]

            parts = parts[0].split("_b_")
            block_id = parts[1]

            parts = parts[0].split("c_")
            course_id = parts[1]

            course = Course.objects.get(id=course_id)
            block = Block.objects.get(id=block_id)

            if not block.external_tool_view:
                raise Exception("Block does not have an ExternalToolView.")
            external_tool_view = block.external_tool_view

            user = User.objects.get(anon_username=user_anon_username)
        except Exception as e:
            logger.error(f"Error econstructing login hint : {login_hint}. {e}")
            raise Exception("Cannot deconstruct login hint")

        return course, external_tool_view, user

    def authorize_tool_and_generate_claims(
        self,
        tool_request: ToolAuthRequestData,  # noqa: F841
        external_tool_view: ExternalToolView,
        user: User,
    ) -> dict:  # noqa: F841
        """
        Authorize a user to access the tool resource in the context of a particular
        unit in a course (represented by this instance's external_tool_view) and return the
        claims data that should be included.

        This is the second step in the LTI 1.3 OIDC login process, where we've
        already sent the initial login request to the external tool (step #1), and
        now the tool is calling back to us at this URL to get an "ID token"

        If all is well, we'll return an instance of the LTI1v3ClaimsData class
        which contains all the 'claims' that should be embedded in the ID token
        that we'll return to the client (via an auto-posting form).

        Args:
            tool_request:               The request data from the external tool that we're responding to.
            external_tool_provider:     The ExternalToolProvider instance that represents the tool.
            user:                       The user that is requesting access to the tool.

        Returns:
            LTI1v3ClaimsData: The claims data that should be included in the JWT token.

        """

        # TODO: Craft helpful exception classes and raise below where requried

        # TODO: AUTHENTICATE
        #   How do we make sure the request is valid in terms of LTI 1.3
        #   and the user is authenticated before proceeding?

        etp: ExternalToolProvider = self.external_tool_provider
        if external_tool_view.external_tool_provider != etp:
            # This service is currently tied to a single ExternalToolProvider
            # So we need to make sure the ExternalToolView is associated with the same one.
            # (There could be external tool views with different providers in the same course,
            # in which case the caller should have configured this service with the correct
            # provider before calling this method.)
            raise Exception("ExternalToolView has a different ExternalToolProvider.")

        # TODO: Figure out how we can get a full URL back to the course
        #       unit that the user was on when they clicked the link.
        course_unit_url = None

        site_profile: SiteProfile = get_current_site_profile()

        # BASIC LTI 1.3 CLAIMS...
        # Prepare basic LTI 1.3 claims (replace with your actual data)
        claims_dc = LTI1v3ClaimsData()
        claims_dc.nonce = tool_request.nonce
        claims_dc.set_timestamp()  # sets the 'iat' and 'exp'
        claims_dc.iss = etp.issuer
        claims_dc.aud = str(etp.client_id)
        claims_dc.sub = etp.get_sub(user)

        claims = asdict(claims_dc)

        # EXTRA LTI 1.3 CLAIMS...
        # Add extra claims for LTI 1.3
        lti_v3_1_claims = {
            LTIParamName.DEPLOYMENT_ID.value: etp.deployment_id,
            # Per LTIv1.3 spec, this should be 'LtiResourceLinkRequest'
            LTIParamName.MESSAGE_TYPE.value: "LtiResourceLinkRequest",
            # We're only supporting LTIv1.3 for now
            LTIParamName.LTI_VERSION.value: "1.3.0",
            LTIParamName.ROLES.value: [
                # Static value for now until we figure out options
                LTI1P3InstitutionCoreRoles.STUDENT.value
            ],
            LTIParamName.CONTEXT.value: {
                "id": self.course.token,
                "label": self.course.token,
                "title": self.course.display_name,
                "type": [LTIContextType.COURSE_OFFERING.value],
            },
            LTIParamName.RESOURCE_LINK.value: {
                "id": self.external_tool_view.resource_link_id,
                # title and description are optional
                # "title": self.external_tool_view.title,
                # "description": self.external_tool_view.description,
            },
            LTIParamName.TOOL_PLATFORM.value: {
                "guid": site_profile.uuid,
                "contact_email": settings.CONTACT_EMAIL,
                "description": site_profile.description,
                "name": site_profile.site.name,
                "url": site_profile.site.domain,
                # Not sure what 'product_family_code' is...
                # "product_family_code": "ExamplePlatformVendor-Product",
                # Don't need version...
                #"version": "1.0",
            },
            LTIParamName.TARGET_LINK_URI.value: etp.launch_uri,
            LTIParamName.LAUNCH_PRESENTATION.value: {
                "document_target": self.external_tool_view.launch_type,
                "return_url": course_unit_url,
                # "height": 400,
                # "width": 800,
            },
            LTIParamName.CUSTOM.value: {
                # DMcQ: Using this for testing with JupyterHub
                # See: https://ltiauthenticator.readthedocs.io/en/latest/lti13/getting-started.html
                "lms_username": user.username,
            }

            # TODO:
            #LTIParamName.LIS.value: {
            #    LTIParamName.LIS_PERSON_SOURCE_ID.value: "example.edu:71ee7e42-f6d2-414a-80db-b69ac2defd4",
            #    LTIParamName.LIS_COURSE_OFFERING_ID.value: "example.edu:SI182-F16",
            #    LTIParamName.LIS_COURSE_SECTION_ID.value: "example.edu:SI182-001-F16"
            #},
            # TODO: Consider other claims:
            # "given_name": "Meh",
            # "family_name": "Average",
            # "name": "Meh Average",
            # "email": "meh@example.com"
            # LTIParamName.TOOL_PLATFORM.value: {
            #     "guid": "12345",
            #     "name": "Some LMS",
            #     "product_family_code": "KinesinLMS"
            # }
            # TODO: Implement claim for AGS scope
            # See examples in the LTI 1.3 spec https://www.imsglobal.org/spec/lti-ags/v2p0#example-service-claims  ...
            # This claim MUST be included in LTI messages if any of the Assignment
            # and Grade Services are accessible by the tool in the context of the LTI message.
            # LTIParamName.ENDPOINT.value: {
            #   "scope": [
            #
            #   ]
            # }
            # TODO: Do we need names roles service
            # "https://purl.imsglobal.org/spec/lti-nrps/claim/namesroleservice": {
            #   "context_memberships_url": "https://demo.moodle.net/mod/lti/services.php/CourseSection/47/bindings/2/memberships",
            #   "service_versions": ["1.0", "2.0"]
            # }
        }

        claims |= lti_v3_1_claims

        return claims

    def generate_external_tool_launch(
        self,
        claims: LTI1v3ClaimsData,
        tool_request: ToolAuthRequestData,
    ) -> ExternalToolLaunchData:
        """
        Generate the external tool launch URL. Creates an instance of the
        ExternalToolLaunchData class that contains the necessary data to launch
        the external tool after it has been validated as part of the LTI 1.3 OIDC login process.

        Args:
            claims:         The claims data that should be included in the JWT token.
            tool_request:   The request data from the external tool that we're responding to.

        Returns:
            ExternalToolLaunchData: An instance of the ExternalToolLaunchData class.

        """

        launch_data = ExternalToolLaunchData(
            claims=claims,
            deployment_id=self.external_tool_provider.deployment_id,
            launch_url=self.external_tool_provider.launch_uri,
            # The tool sends us the state in the login callback
            # and then we send it back in the tool launch.
            state=tool_request.state,
        )

        return launch_data
