import logging
from django.conf import settings
from django.shortcuts import render
from django.views import View
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.utils.translation import gettext as _
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from django.contrib.auth.decorators import login_required
from kinesinlms.learning_library.models import UnitBlock
from kinesinlms.course.models import Course, Enrollment, CourseUnit
from kinesinlms.external_tools.models import ExternalToolProvider, ExternalToolView
from kinesinlms.lti.models import ToolAuthRequestData
from kinesinlms.lti.service import ExternalToolLTIService
from kinesinlms.course.utils_access import can_access_course

logger = logging.getLogger(__name__)

# Views for use by External Tool
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class LTIAuthorizeRedirect(View):
    """
    This view handles the external tool's initial OIDC callback for LTIv1.3.
    It's not for direct access by the KinesinLMS user.
    Remember that LTIv1.3 follows the "third party initiated flow" variant of the OIDC process.
    """

    def get(self, request, *args, **kwargs):
        """
        This URL handles the second step in the LTI 1.3 OIDC login process,
        where we've already done the login request to the external tool (step #1),
        and now the external tool is calling back to us at this URL to get an "ID token."

        According to the LTI 1.3 standard, we should expect a few things in
        this request:
            - nonce:                A nonce that we sent in the initial 'login' request
            - lti_message_hint:     The lti_message_hint we sent in the initial 'login' request
            - login_hint:           The login_hint we sent in the initial 'login' request


        Args:
            request:    The request from the external tool.

        Returns:
            HTTP response with autosubmit template. This continues the OIDC login process.
        """

        # Parse the initial request from the tool
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        try:
            tool_request: ToolAuthRequestData = self._parse_initial_tool_request(
                request
            )
        except Exception:
            message = "Error parsing initial request"
            logger.exception(message)
            return HttpResponse(status=400, content=_(message))

        # We can locate the relevant ExternalToolProvider by the client_id
        # passed in from the tool...
        try:
            external_tool_provider = ExternalToolProvider.objects.get(
                client_id=tool_request.client_id
            )
        except ExternalToolProvider.DoesNotExist:
            logger.error(f"client_id {tool_request.client_id} not found.")
            message = _(
                "External Tool Provider with client_id %(client_id)s not found."
            ) % {"client_id": tool_request.client_id}
            return HttpResponse(status=400, content=message)

        # TODO:
        #   Eventually, we should be able to support multiple redirect URIs
        #   for an external tool. For now, just validate against the one possible redirect URI.
        if tool_request.redirect_uri != external_tool_provider.launch_uri:
            logger.error(
                f"Redirect URI {tool_request.redirect_uri} != provider launch uri {external_tool_provider.launch_uri}"
            )
            user_message = _(
                "Redirect URI %(redirect_uri)s does not match "
                "External Tool Provider %(launch_uri)s"
            ) % {
                "redirect_uri": tool_request.redirect_uri,
                "launch_uri": external_tool_provider.launch_uri,
            }
            return HttpResponse(status=400, content=user_message)

        # Do base OIDC validation
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # TODO:
        #   Is there some kind of library that can do this for us? Ugh.

        # Deconstruct the login hint to get component parts. The ExternalToolView is probably
        # relevant here as we may want info from the exact place this tool was launched, and
        # not just the more generic information stored in ExternalToolProvider. (The same tool
        # may be embedded multiple times in the same course.)
        try:
            course, external_tool_view, user = (
                ExternalToolLTIService.deconstruct_login_hint(tool_request.login_hint)
            )
        except Exception:
            # TODO: Handle different types of Exceptions (we have yet to define)
            message = "Error deconstructing login hint"
            logger.exception(message)
            return HttpResponse(status=400, content=_(message))

        # Initialize our service class, so it can do most of the remaining work in this process.
        service = ExternalToolLTIService(
            external_tool_view=external_tool_view,
            course=course,
        )

        # Authorize the request and get the claims data
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        try:
            lti_claims: dict = service.authorize_tool_and_generate_claims(
                tool_request=tool_request,
                external_tool_view=external_tool_view,
                user=user,
            )
        except Exception:
            # TODO Handle different types of Exceptions (we have yet to define)
            message = "Error authorizing tool access"
            logger.exception(message)
            return HttpResponse(status=400, content=_(message))

        # Generate 'launch' info including JWT and return it to user's browser with
        # an autosubmit form to send the user back to the tool
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        external_tool_launch_data = service.generate_external_tool_launch(
            claims=lti_claims,
            tool_request=tool_request,
        )

        # Prepare information for auto-submitting form
        context = {
            "external_tool_view": external_tool_view,
            "external_tool_launch_data": external_tool_launch_data,
        }

        # Redirect to launch URL with access token in JWT
        return render(request, "lti/external_tool_launch.html", context)

    def _parse_initial_tool_request(self, request) -> ToolAuthRequestData:
        """
        Parse the initial OIDC auth request from the tool.

        Validate all the things and return a ToolAuthRequestData object
        if all is well.

        Args:
            request:    The request from the external tool.

        Returns:
            ToolAuthRequestData:    The parsed data from the request.
        """

        tool_request_params = request.GET if request.method == "GET" else request.POST
        logger.debug(f"Tool request params: {tool_request_params}")

        # TODO: Validation and such...

        # This information should be in the request according to LTIv1.3
        client_id = tool_request_params.get("client_id")
        redirect_uri = tool_request_params.get("redirect_uri")
        login_hint = tool_request_params.get("login_hint")
        # TODO: Do we need to require lti_message_hint to be set and returned?
        lti_message_hint = tool_request_params.get("lti_message_hint", None)

        # This nonce is supposed to be related to a 'xsrf' cookie
        # set by the tool in the user's browser.
        nonce = tool_request_params.get("nonce")

        state = tool_request_params.get("state")

        data = ToolAuthRequestData(
            client_id=client_id,
            redirect_uri=redirect_uri,
            login_hint=login_hint,
            nonce=nonce,
            lti_message_hint=lti_message_hint,
            state=state,
        )

        return data


lti_authorize_redirect = LTIAuthorizeRedirect.as_view()


class JwksInfoView(View):
    """
    Provide JWKS information for the tool provider.
    """

    def get(self, request, *args, **kwargs):
        if settings.LTI_PLATFORM_PRIVATE_KEY:
            # Load PEM-encoded private key
            private_key_data = settings.LTI_PLATFORM_PRIVATE_KEY.encode("utf-8")
            try:
                private_key = serialization.load_pem_private_key(
                    private_key_data,
                    password=None,
                    backend=default_backend(),
                )
            except Exception as e:
                logger.error(f"Error loading private key: {e}")
                return HttpResponse(
                    status=500, content="Error loading key information."
                )

            # Extract public key
            public_key = private_key.public_key()

            # Extract public key parameters
            public_key_n = public_key.public_numbers().n
            public_key_e = public_key.public_numbers().e

            # Construct JWKS
            jwks = {
                "keys": [
                    {
                        "kty": "RSA",
                        "e": base64.urlsafe_b64encode(
                            public_key_e.to_bytes((public_key_e.bit_length() + 7) // 8)
                        ).decode(),
                        "use": "sig",
                        "kid": "lti1.3-key",
                        "alg": "RS256",
                        "n": base64.urlsafe_b64encode(
                            public_key_n.to_bytes((public_key_n.bit_length() + 7) // 8)
                        ).decode(),
                    }
                ]
            }

            # Create JSON response
            response = JsonResponse(jwks)

            # Set CORS headers
            response["Access-Control-Allow-Origin"] = "*"

            # Set Cache-Control headers
            response["Cache-Control"] = (
                "public, "
                + f"max-age={settings.LTI_PLATFORM_JWKS_MAX_AGE_SECONDS}, "
                + f"stale-while-revalidate={settings.LTI_PLATFORM_JWKS_MAX_AGE_SECONDS}, "
                + f"stale-if-error={settings.LTI_PLATFORM_JWKS_MAX_AGE_SECONDS}"
            )
            return response
        else:
            return JsonResponse({"keys": []})


jwks_info_view = JwksInfoView.as_view()


# Views for KinesinLMS Templates
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@login_required
def lti_launch(
    request,
    course_slug: str,
    course_run: str,
    course_unit: int,
    block_id: int,
):
    """
    This view is the first step in the LTI login process. It's called by the
    user clicking an HTMx-enabled button in the course unit. This view
    will then perform the first part of the OIDC login process with the
    external tool. If all goes well, the external tool will
    The user will be sent to this URL in order to initiate the LTI login process.

    Args:
        request:        The request from the user.
        course_slug:    The slug of the course.
        course_run:     The run of the course.
        course_unit:    The ID of the course unit.
        block_id:       The ID of the block.

    Returns:
        HTTP response that redirects the user to the external tool's login URL.

    """

    # As with any request for unit content, we have to make sure user
    # has access to the course and unit at the current time.

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    if request.user.is_superuser or request.user.is_staff:
        pass
    else:
        enrollment = get_object_or_404(
            Enrollment,
            student=request.user,
            course=course,
            active=True,
        )
        if not can_access_course(request.user, course, enrollment=enrollment):
            raise PermissionDenied()

    try:
        course_unit = CourseUnit.objects.get(pk=course_unit, course=course)
    except CourseUnit.DoesNotExist:
        raise PermissionDenied()

    try:
        unit_block = UnitBlock.objects.get(block_id=block_id, course_unit=course_unit)
    except ExternalToolView.DoesNotExist:
        logger.error(
            f"ExternalToolView with block_id {block_id} "
            f"and course_unit {course_unit} not found."
        )
        return HttpResponse(status=400)

    try:
        block = unit_block.block
        external_tool_view = getattr(block, "external_tool_view", None)
        if not external_tool_view:
            raise Exception("No ExternalToolView found.")
    except Exception as e:
        logger.error(f"Error getting ExternalToolView: {e}")
        return HttpResponse(status=400)

    lti_service = ExternalToolLTIService(
        external_tool_view=external_tool_view, course=course
    )

    # Build the login URL for the external tool with the required GET
    # parameters for the OIDC login process.
    login_url = lti_service.get_tool_login_url(user=request.user, external_tool_view=external_tool_view)

    return redirect(login_url)
