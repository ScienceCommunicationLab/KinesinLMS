import logging
from django.conf import settings
from django.shortcuts import render
from django.views import View
from django.http import HttpResponse, JsonResponse
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from kinesinlms.external_tools.models import ExternalToolProvider
from kinesinlms.lti.models import (
    LTI1v3ClaimsData,
    ToolAuthRequestData,
)
from kinesinlms.lti.service import ExternalToolLTIService
import base64

logger = logging.getLogger(__name__)


class LTIAuthorizeRedirect(View):  # OAuthLibMixin,
    """
    This view handles the tool's initial OIDC callback for LTIv1.3. Remember that LTIv1.3
    follows the "third party initiated flow" variant of the OIDC process.

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
        except Exception as e:
            logger.error(f"Error parsing initial request: {e}")
            return HttpResponse(status=400)

        # We can locate the relevant ExternalToolProvider by the client_id
        # passed in from the tool...
        try:
            external_tool_provider = ExternalToolProvider.objects.get(
                client_id=tool_request.client_id
            )
        except ExternalToolProvider.DoesNotExist:
            logger.error(
                f"External Tool Provider with client_id {tool_request.client_id} not found."
            )
            return HttpResponse(status=400)

        # TODO:
        #   Eventually, we should be able to support multiple redirect URIs
        #   for an external tool. For now, just validate against the one possible redirect URI.
        if tool_request.redirect_uri != external_tool_provider.launch_uri:
            logger.error(
                f"Redirect URI {tool_request.redirect_uri} does not match "
                f"External Tool Provider {external_tool_provider.launch_uri}"
            )
            return HttpResponse(status=400)

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
        except Exception as e:
            # TODO: Handle different types of Exceptions (we have yet to define)
            logger.error(f"Error deconstructing login hint: {e}")
            return HttpResponse(status=400)

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
        except Exception as e:
            # TODO Handle different types of Exceptions (we have yet to define)
            logger.error(f"Error authorizing tool access: {e}")
            return HttpResponse(status=400)

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
            private_key = serialization.load_pem_private_key(
                private_key_data, password=None, backend=default_backend()
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
