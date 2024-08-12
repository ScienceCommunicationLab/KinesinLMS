import logging

import environ
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from unittest import skipUnless

from kinesinlms.email_automation.constants import EmailAutomationProviderType
from kinesinlms.email_automation.models import EmailAutomationProvider
from kinesinlms.email_automation.service import ActiveCampaignService
from kinesinlms.users.tests.factories import UserFactory

from allauth.account.models import EmailAddress

User = get_user_model()
logger = logging.getLogger(__name__)

TEST_USER_NAME = "test-student"
TEST_USER_PW = "test-student-pw-123"
TEST_USER_EMAIL = "test-student@example.com"

env = environ.Env()

# This test assumes a contact already exists in AC with the following email
DEFAULT_EXISTING_CONTACT_EMAIL = "test@example.com"


class TestActiveCampaignServiceIntegration(StaticLiveServerTestCase):
    """
    Test the ActiveCampaign integration using a live (test) account
    and the AC service.

    This test expects the following environment variables to be set:
    - EMAIL_AUTOMATION_PROVIDER_API_KEY (expected by Django)
    - EMAIL_AUTOMATION_PROVIDER_URL     (used only by integration tests like this)
    - EXISTING_AC_CONTACT_EMAIL     An email of a test contact already set up in AC.
                                    If not defined, the test uses the value stored
                                    in DEFAULT_EXISTING_CONTACT_EMAIL.



    """

    existing_user = None
    provider = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        api_url = env("TEST_EMAIL_AUTOMATION_PROVIDER_URL")
        
        provider = EmailAutomationProvider.objects.create(
            type=EmailAutomationProviderType.ACTIVE_CAMPAIGN.name,
            active=True,
            api_url=api_url,
            site_id=settings.SITE_ID,
        )
        existing_user_email = DEFAULT_EXISTING_CONTACT_EMAIL
        cls.existing_user = UserFactory.create(email=existing_user_email)
        cls.provider = provider

        EmailAddress.objects.create(
            user=cls.existing_user,
            email=existing_user_email,
            primary=True,
            verified=True,
        )

        # Make sure the existing user is set up in AC
        service = ActiveCampaignService(cls.provider)
        try:
            ac_id = service.add_contact(cls.existing_user)
            cls.existing_user.email_automation_provider_user_id = ac_id
            cls.existing_user.save()
        except Exception:
            pass

    @skipUnless(
        settings.EMAIL_AUTOMATION_PROVIDER_API_KEY,
        "Email automation provider not configured",
    )
    def test_api_connection(self):
        service = ActiveCampaignService(self.provider)
        result = service.test_api_connection()
        self.assertTrue(result)

    @skipUnless(
        settings.EMAIL_AUTOMATION_PROVIDER_API_KEY,
        "Email automation provider not configured",
    )
    def test_get_contact_id(self):
        existing_user_email = self.existing_user.email
        service = ActiveCampaignService(self.provider)
        contact_id = service.get_contact_id(existing_user_email)
        self.assertIsNotNone(contact_id)

    @skipUnless(
        settings.EMAIL_AUTOMATION_PROVIDER_API_KEY,
        "Email automation provider not configured",
    )
    def test_add_contact(self):
        """
        Let's say we have a new user, and we want to add them to the email automation provider.
        """
        service = ActiveCampaignService(self.provider)
        email = "new_user@example.com"
        new_user = UserFactory.create(email=email)

        EmailAddress.objects.create(
            user=new_user,
            email=new_user.email,
            primary=True,
            verified=True,
        )
        ac_id = service.add_contact(new_user)
        self.assertIsNotNone(ac_id)

    @skipUnless(
        settings.EMAIL_AUTOMATION_PROVIDER_API_KEY,
        "Email automation provider not configured",
    )
    def test_add_tag_to_contact(self):
        """
        Tests adding a tag that does not exist in AC to the existing user.
        This should both create the tag in AC and then add it to the contact.
        """

        tag = "new-tag-does-not-exist-in-AC-yet"

        # Makr sure the tag doesn't exist yet locally
        if self.provider.tag_ids and tag in self.provider.tag_ids:
            raise Exception("Tag already exists in provider.tag_ids")

        service = ActiveCampaignService(self.provider)
        result = service.add_tag_to_contact(self.existing_user, tag)
        self.assertTrue(result)

    @skipUnless(
        settings.EMAIL_AUTOMATION_PROVIDER_API_KEY,
        "Email automation provider not configured",
    )
    def test_remove_tag_from_contact(self):
        """
        Tests both getting tags for a user and removing one
        of those tags.
        """

        service = ActiveCampaignService(self.provider)

        # Create a tag in AC and assign it to user
        tag = "finished-course-tag"
        service.add_tag_to_contact(self.existing_user, tag)

        # Create another tag that shouldn't be deleted
        do_not_delete_tag = "another-tag-do-not-delete"
        service.add_tag_to_contact(self.existing_user, do_not_delete_tag)

        # Prove that both tags are there
        tags = service.get_tags_for_contact(self.existing_user)
        self.assertTrue(tag in tags)
        self.assertTrue(do_not_delete_tag in tags)

        # Now delete the tag ...
        service = ActiveCampaignService(self.provider)
        result = service.remove_tag_from_contact(self.existing_user, tag)
        self.assertTrue(result)

        # Prove that tag is not there anymore
        tags = service.get_tags_for_contact(self.existing_user)
        self.assertFalse(tag in tags)

        # Prove that other tag is still there.
        self.assertTrue(do_not_delete_tag in tags)
