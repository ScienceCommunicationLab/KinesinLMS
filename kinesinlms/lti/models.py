from dataclasses import dataclass, asdict
from enum import Enum
import time

from django.conf import settings
import jwt


@dataclass
class LTIToolLoginData:
    """
    Dataclass to represent the login data that is sent to the external tool.
    """

    # TODO: Add validations and such to justify use of dataclass.

    # PARAMS DEFINED BY OpenID SPEC
    # .........................................

    # The 'issuer', which is essentially this KinesinLMS application.
    iss: str = None

    # A 'login hint' represents the user in the context of the current interaction.
    # KinesinLMS includes the course, user and block information in the hint.
    # The tool must return this hint unaltered.
    login_hint: str = None

    # This is the URL we'll be launching on the tool in the second leg of the OIDC
    # workflow, if all is well. Essentially, this is the "real" URL we want to the student
    # to get to once all this craziness is done.
    # Per the LTI 1.3 spec:
    #   The target link URI is the actual endpoint for the LTI resource to display;
    #   for example, the url in Deep Linking ltiResourceLink items, or the launch_url
    #   in IMS Common Cartridges, or any launch URL defined in the tool configuration.
    target_link_uri: str = None

    # ADDITIONAL PARAMS DEFINED BY LTIv1.3 SPEC
    # .........................................

    # These params are not part of the OpenID 3rd Party spec,
    # but are additions defined in the LTI 1.3 spec.

    # Per the LTI 1.3 spec,
    #   The new optional parameter lti_message_hint may be used
    #   alongside the login_hint to carry information about the actual
    #   LTI message that is being launched.
    # The tool must return this hint unaltered.
    lti_message_hint: str = None

    # A deployment ID that is unique to this site. Since KinesinLMS isn't written
    # to be multitenant, we just return the site ID, which is probably '1'.
    lti_deployment_id: str = None

    # The client ID is the opaque ID that represents the tool in KinesinLMS.
    # LTIv1.3 defines this so that an external tool can have multiple registrations
    # for a single tool. In our case, a single tool will have a single registration.
    # We generate this client_id value when the KinesinLMS admin or author creates
    # a new instance of an ExternalToolProvider in the management section of the site.
    # Somebody then needs to set up the external tool so it knows to use this particular
    # client_id for its interactions with KinesinLMS.
    client_id: str = None

    @property
    def params(self) -> dict:
        """
        Returns diction of parameters expected by the external tool.

        Returns:
            Dictionary of parameters
        """
        p = {
            "iss": self.iss,
            "login_hint": self.login_hint,
            "target_link_uri": self.target_link_uri,
            "lti_deployment_id": self.lti_deployment_id,
            "client_id": self.client_id,
            "lti_message_hint": self.lti_message_hint,
        }
        return p


class LTIParamName(Enum):
    DEPLOYMENT_ID = "https://purl.imsglobal.org/spec/lti/claim/deployment_id"
    TARGET_LINK_URI = "https://purl.imsglobal.org/spec/lti/claim/target_link_uri"
    ROLES = "https://purl.imsglobal.org/spec/lti/claim/roles"
    RESOURCE_LINK = "https://purl.imsglobal.org/spec/lti/claim/resource_link"
    LTI_VERSION = "https://purl.imsglobal.org/spec/lti/claim/version"
    MESSAGE_TYPE = "https://purl.imsglobal.org/spec/lti/claim/message_type"
    CONTEXT = "https://purl.imsglobal.org/spec/lti/claim/context"
    LAUNCH_PRESENTATION = "https://purl.imsglobal.org/spec/lti/claim/launch_presentation"
    TOOL_PLATFORM = "https://purl.imsglobal.org/spec/lti/claim/tool_platform"
    ENDPOINT = "https://purl.imsglobal.org/spec/lti/claim/endpoint"


class LTIContextType(Enum):
    COURSE_TEMPLATE = "http://purl.imsglobal.org/vocab/lis/v2/course#CourseTemplate"
    # A "Course Offering" represents a specific instance of a course that is being offered to students during a particular term or period.
    COURSE_OFFERING = "http://purl.imsglobal.org/vocab/lis/v2/course#CourseOffering"
    # A "Course Section" is a subdivision of a course offering. 
    COURSE_SECTION = "http://purl.imsglobal.org/vocab/lis/v2/course#CourseSection"
    # A "Group" refers to a collection of users within a course that is not necessarily tied to a specific section.
    GROUP = "http://purl.imsglobal.org/vocab/lis/v2/course#Group"


@dataclass
class LTI1v3ClaimsData:
    """
    Dataclass to represent the base claims data that is sent to the external tool.
    Some of the comment text below is taken from the IMS Global LTI 1.3 spec.

    Other claims in addition to the ones below may be added to a tool
    response dictionary.

    """

    # The 'issuer', which is essentially this KinesinLMS application.
    iss: str = None

    # The 'audience' of the token, which is the client ID of the external tool.
    aud: str = None

    # The 'subject' of the token, which is the user's anon_username.
    sub: str = None

    # The 'role' of the user in the context of the current interaction.
    # The tool must return this hint unaltered.
    role: str = None

    # Timestamp for when the JWT should be treated as having
    # expired (after allowing a margin for clock skew)
    exp: int = None

    # Timestamp for when the JWT was created
    iat: int = None

    # String value used to associate a Tool session with an ID Token, and to
    # mitigate replay attacks. The nonce is creaetd by the tool and sent in
    # the initial request to the platform. The platform must return this value.
    nonce: str = None

    # OPTIONAL
    # The 'authorized party' of the token, which is the client ID of the external tool.
    # Authorized party - the party to which the ID Token was issued. If present, it MUST contain the OAuth
    # 2.0 Tool ID of this party. This Claim is only needed when the Token has a single audience value and that
    # audience is different than the authorized party. It MAY be included even when the authorized party is
    # the same as the sole audience. The azp value is a case-sensitive string containing a String or URI value.
    # azp: str = None

    def set_timestamp(self, expiration: int = 1000):
        """
        Set the timestamp values for the JWT token.

        Args:
            expiration:    The number of seconds from now that the token should expire.
        """
        if not isinstance(expiration, int):
            raise ValueError("Expiration must be an integer.")
        if expiration < 0:
            raise ValueError("Expiration must be a positive integer.")
        if expiration > 100000:
            raise ValueError("Expiration must be less than 100,000 seconds.")
        self.iat = int(time.time())
        self.exp = self.iat + expiration


@dataclass
class ExternalToolLaunchData:
    """
    Contains the info necessary to launch the external tool after it has been
    validated as part of the LTI 1.3 OIDC login process.

    The launch_params() method below returns the exact dictionary of parameters that
    should be included in an auto-submit form that will send the user back to
    the tool with the JWT token ('id_token').

    This dictionary is mostly just the LTI1v3ClaimsData dataclass as a dictionary,
    but other fields are included as well.

    """

    launch_url: str = None
    deployment_id: str = None
    claims: dict = None
    state: str = None

    @property
    def id_token(self):
        """
        Creates an "ID token" JWT for the LTI message.

        Raises:

        Returns:
            A JWT Token
        """

        claims = self.claims
        if not claims:
            raise ValueError("No LTI claims to encode.")
        if not settings.LTI_PLATFORM_PRIVATE_KEY:
            raise ValueError("No LTI private key to sign with.")

        # Transform into JWT
        id_token_jwt = jwt.encode(
            self.claims,
            settings.LTI_PLATFORM_PRIVATE_KEY,
            algorithm="RS256",
        )
        return id_token_jwt

    @property
    def launch_params(self) -> dict:
        """
        Return the params for the auto-submit form.

        This dictionary has the shape:

        {
            "state": ( state from login response )
            "id_token": ( encoded LTI 'message')
        }

        """

        params = {
            "state": self.state,
            "id_token": self.id_token,
        }

        return params


@dataclass
class ToolAuthRequestData:
    """
    This is the data that we expect to receive from the external tool when we're
    in step 2 of the LTIv1.3 OIDC login process, where the tool is calling back to us
    to get an "ID token."
    """

    # The scope is the set of permissions that the tool is requesting.
    # This is currently only 'openid' in the LTI 1.3 standard.
    scope: str = None

    # The client_id is the opaque ID that represents the tool in KinesinLMS.
    # We generate this client_id value when the KinesinLMS admin or author creates
    # a new instance of an ExternalToolProvider in the management section of the site.
    # (One would then expect the admin to give this client_id to the tool provider to use
    # for registering KinesinLMS in the tool as a valid platform for that tool.)
    client_id: str = None

    # The redirect_uri is the URL that the tool is expecting to be redirected to
    # This must match the redirect_uri that KinesinLMS sent in the initial login request.
    redirect_uri: str = None

    # The login_hint property is required by the LTI1.3 standard.
    # It's meant to be an opaque string that the tool simply returns
    # back to us. We use it to carry information about the user, course,
    # and block that the user is interacting with.
    login_hint: str = None

    # lti_message_hint is not required by the standard.
    # If used, it's meant to be opaque to the tool and only relevant
    # to KinensinLMS.
    lti_message_hint: str = None

    nonce: str = None

    # TODO: Clarify.
    #   I think this it a property generated by the tool which we need to return.
    #   (Not something we send as part of the initial logic)
    state: str = None
