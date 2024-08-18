import logging
import urllib.parse
from django.test import TestCase
from django.urls import reverse
from django.test import Client
from bs4 import BeautifulSoup
import jwt

from kinesinlms.external_tools.tests.factories import (
    ExternalToolProviderFactory,
    ExternalToolViewFactory,
)
from kinesinlms.lti.service import ExternalToolLTIService
from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.users.models import User
from kinesinlms.learning_library.models import Block, BlockType
from kinesinlms.external_tools.constants import ExternalToolViewLaunchType
from kinesinlms.course.models import CourseUnit
from kinesinlms.lti.models import LTIParamName

logger = logging.getLogger(__name__)


class TestLTILaunchProcess(TestCase):
    """
    Test the various steps in the LTI v1.3 launch process.

    This test case is based on the IMS Global LTI 1.3 Advantage specification:
    https://www.imsglobal.org/spec/lti/v1p3

    My hope is this test reminds me of the details of each step in the process.
    Usually I get it after my first coffee but it's gone again at lunch.

    """

    enrolled_user = None
    course = None

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        course = CourseFactory()
        cls.course = course
        enrolled_user = User.objects.create(username="enrolled-user")
        cls.enrolled_user = enrolled_user

        # PROVIDER
        # Create an ExternalToolProvider to represent our mythical external tool.
        external_tool_provider = ExternalToolProviderFactory()
        cls.external_tool_provider = external_tool_provider

        # COURSE BLOCK
        # Make the first block in the course an "External tool view"
        # that would be used to launch the external tool.
        first_unit = CourseUnit.objects.filter(course=course).first()

        block: Block = first_unit.contents.first()
        block.type = BlockType.EXTERNAL_TOOL_VIEW.name
        block.save()
        cls.block = block

        # Link block to an ExternalToolView, which is what we do
        # to give a block a connection to a *particular view or resource*
        # in an external tool.
        external_tool_view = ExternalToolViewFactory(
            external_tool_provider=external_tool_provider,
            block=block,
            launch_type=ExternalToolViewLaunchType.WINDOW.name,
        )
        cls.external_tool_view = external_tool_view

        # LTI SERVICE
        # Create the service class that makes the LTI connection with the tool.
        external_tool_service = ExternalToolLTIService(
            external_tool_view=external_tool_view,
            course=course,
        )
        cls.external_tool_service = external_tool_service

    def setUp(self):
        pass

    def test_login_url(self):
        """
        The first step in an LTIv1.3 launch is to get the external tool to
        log back into the KinesinLMS. This is sometimes called the "login request."
        Make sure we're creating the correct data in this request that's going
        out to the tool.
        """
        login_url = self.external_tool_service.get_tool_login_url(
            user=self.enrolled_user
        )
        logger.info(f"Login URL: {login_url}")
        self.assertTrue(login_url)

        # Parse the URL to check the query parameters
        parsed_url = urllib.parse.urlparse(login_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # List of expected parameters

        # See the docs on the LTIToolLoginData dataclass for more
        # details about these params.
        expected_params = [
            # 'iss' : Issuer
            #   This value should match the iss value in the LTI registration
            #   to ensure that the request is coming from an authorized issuer.
            "iss",
            # 'login_hint' : Login hint
            #  This is the login_hint parameter from the OIDC request.
            #  It is optional, but we do use it in our implementation.
            "login_hint",
            # 'target_link_uri'
            # The URL where the LTI tool should redirect the user to after authentication.
            # This should be a callback URL defined on the KinesinLMS side.
            "target_link_uri",
            # 'lti_message_hint' : LTI message hint
            "lti_message_hint",
            # 'lti_deployment_id'
            #   This is the deployment ID of the LTI tool. It is used to identify
            #   the deployment of the tool that is making the request.
            "lti_deployment_id",
            # 'client_id'
            # This identifies the platform to the tool. So the tool is supposed to already
            # know this value and be able to validate it according to it's internal setup.
            "client_id",
        ]

        # Check if each expected parameter is present in the query string
        for param in expected_params:
            self.assertIn(param, query_params, f"Missing expected parameter: {param}")

        # Optionally, you can check for the presence of specific values
        # if you have predefined expectations for them. For example:
        # self.assertEqual(query_params.get('response_type'), ['code'])

    def test_receive_login_response(self):
        """
        The second step in an LTIv1.3 launch is to receive the login response
        from the tool. This is where the tool sends the user back to the platform
        with an ID token.

        If all goes well, the response from KinesinLMS should be to redirect the user
        back to the final destination on the external tool (the 'redirect URI') so
        they can view the external resource. 

        This test makes sure the auto-submitting form is being generated correctly
        and contains the correct 'state' values.
        
        As part of this launch, KinesinLMS includes a bunch of 'claims' LTI expects
        us to send to the external tool, so this test makes sure those claims are in
        the request to the tool and have values we (and the tool) would expect.

        The term 'claim' is interesting because you would think by this point we would
        be telling the tool "here's a bunch of 'truths' not just 'claims'", but my understanding
        is that in the world of OpenID, the receiver (in this case, the tool) of a message 
        needs to evaluate and trust based on certain conditions. The receiver has to validate
        the signature and decide whether to trust the issuer. Therefore, only the tool
        can say the 'claims' are indeed 'truths'.

        ...at least, that's my understanding at the moment.
        """

        authorize_redirect_uri = reverse("lti:lti_authorize_redirect")

        expected_login_hint = (
            f"c_{self.course.id}_b_{self.block.id}_u_{self.enrolled_user.anon_username}"
        )

        # These are the parameters that the tool sends back to us
        # after the user has authenticated.
        request_from_tool_params = {
            "scope": "openid",
            "response_type": "id_token",
            "client_id": self.external_tool_provider.client_id,
            "redirect_uri": self.external_tool_provider.launch_uri,
            "login_hint": expected_login_hint,
            # Represents the state parameter from OAuth flow, for CSRF mitigation
            # This is just a CSRF token.
            "state": "sample-state",
            # LTIv1.3 requires response mode to always be 'form_post'
            "response_mode": "form_post",
            "nonce": "sample-nonce",
            "prompt": "none",  # The platform should not prompt the user for authentication again
            "lti_message_hint": expected_login_hint,
        }

        # Create a test client to simulate the HTTP request
        client = Client()

        # Make a GET request to the authorize redirect URL
        response = client.get(authorize_redirect_uri, request_from_tool_params)

        # The view should return a response that contains a form that
        # submits the ID token back to the tool.
        self.assertEqual(response.status_code, 200, "Expected a 200 response")

        # Use BeautifulSoup to parse the response content
        soup = BeautifulSoup(response.content, "html.parser")

        # Find the form element and assert the action attribute is correct
        form = soup.find(
            "form", {"id": f"external-tool-launch-{self.external_tool_view.id}"}
        )
        self.assertIsNotNone(form, "Expected the form to be present in the response")

        expected_form_action = "https://example.com/launch"
        self.assertEqual(
            form["action"], expected_form_action, "The form action URL is incorrect"
        )

        # Verify that the form contains the correct input fields with the correct values
        state_input = form.find("input", {"name": "state"})
        self.assertIsNotNone(
            state_input, "Expected 'state' input to be present in the form"
        )
        self.assertEqual(
            state_input["value"], "sample-state", "The 'state' input value is incorrect"
        )

        id_token_input = form.find("input", {"name": "id_token"})
        self.assertIsNotNone(
            id_token_input, "Expected 'id_token' input to be present in the form"
        )

        # Decode the JWT to verify it contains the correct claims (example verification)
        decoded_jwt = jwt.decode(
            id_token_input["value"], options={"verify_signature": False}
        )
        self.assertEqual(
            decoded_jwt["iss"],
            self.external_tool_provider.issuer,
            "The 'iss' claim in the JWT is incorrect",
        )
        self.assertEqual(
            decoded_jwt["aud"],
            str(self.external_tool_provider.client_id),
            "The 'aud' claim in the JWT is incorrect",
        )
        self.assertEqual(
            decoded_jwt["sub"],
            self.enrolled_user.username,
            "The 'sub' claim in the JWT is incorrect",
        )
        self.assertTrue(
            isinstance(decoded_jwt["exp"], int),
            "The 'exp' claim in the JWT is not an integer",
        )
        self.assertTrue(
            isinstance(decoded_jwt["iat"], int),
            "The 'iat' claim in the JWT is not an integer",
        )
        self.assertEqual(
            decoded_jwt["nonce"],
            "sample-nonce",
            "The 'nonce' claim in the JWT is not an integer",
        )
        self.assertEqual(
            decoded_jwt[LTIParamName.DEPLOYMENT_ID.value],
            "1",
            f"The '{LTIParamName.DEPLOYMENT_ID.value}' claim in the JWT is incorrect",
        )
        self.assertEqual(
            decoded_jwt[LTIParamName.TARGET_LINK_URI.value],
            "https://example.com/launch",
            f"The '{LTIParamName.TARGET_LINK_URI.value}' claim in the JWT is incorrect",
        )
        self.assertEqual(
            decoded_jwt[LTIParamName.ROLES.value],
            ["http://purl.imsglobal.org/vocab/lis/v2/membership#Learner"],
            f"The '{LTIParamName.ROLES.value}' claim in the JWT is incorrect",
        )
        self.assertEqual(
            decoded_jwt[LTIParamName.CONTEXT.value],
            {
                "id": "TEST_SP",
                "label": "TEST_SP",
                "title": "Test Course (Self-Paced)",
                "type": [
                    "http://purl.imsglobal.org/vocab/lis/v2/course#CourseOffering"
                ],
            },
            f"The '{LTIParamName.CONTEXT.value}' claim in the JWT is incorrect",
        )
        # The ID used in the resource link should be the resource_link_id defined in the ExternalToolView.
        self.assertEqual(
            decoded_jwt[LTIParamName.RESOURCE_LINK.value],
            {"id": self.external_tool_view.resource_link_id},
            f"The '{LTIParamName.RESOURCE_LINK.value}' claim in the JWT is incorrect",
        )
        self.assertEqual(
            decoded_jwt[LTIParamName.LTI_VERSION.value],
            "1.3.0",
            f"The '{LTIParamName.LTI_VERSION.value}' claim in the JWT is incorrect",
        )
        self.assertEqual(
            decoded_jwt[LTIParamName.MESSAGE_TYPE.value],
            "LtiResourceLinkRequest",
            f"The '{LTIParamName.MESSAGE_TYPE.value}' claim in the JWT is incorrect",
        )
        self.assertEqual(
            decoded_jwt[LTIParamName.LAUNCH_PRESENTATION.value],
            {"document_target": "WINDOW", "return_url": None},
            f"The '{LTIParamName.LAUNCH_PRESENTATION.value}' claim in the JWT is incorrect",
        )
