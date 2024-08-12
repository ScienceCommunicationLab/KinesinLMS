import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict

from kinesinlms.email_automation.clients.active_campaign_client import (
    ActiveCampaignClient,
)
from kinesinlms.email_automation.models import EmailAutomationProvider
from allauth.account.models import EmailAddress

logger = logging.getLogger(__name__)


class EmailAutomationService(ABC):
    provider: Optional[EmailAutomationProvider] = None

    def __init__(self, provider: EmailAutomationProvider):
        if not provider:
            raise ValueError("provider argument is required")
        self.provider = provider

    @abstractmethod
    def test_api_connection(self) -> bool:
        """
        Test the connection to an Email Automation Service.

        Returns:
            True if connection is successful, False otherwise.
        """
        pass

    @abstractmethod
    def get_contact_id(self, email) -> str:
        pass

    @abstractmethod
    def add_contact(self, user, authorized_email: str = None) -> Optional[str]:
        """
        This method should be created in subclass to add a contact to
        the target email automation service.

        If one already exists this method should sync our model to the latest data
        (e.g. identifier) in the remote email automation service.

        The reason we ask for the authorized email as an argument
        (and don't just use the email associated with 'user') is because
        each user can have multiple emails defined by Allauth.
        So we want to allow the caller to say exactly which email to use.

        But if authorized_email isn't provided, we'll just use
        the default EmailAddress associated with user.

        Args:
            user:                   A User object.
            authorized_email:       Email authorized by Allauth

        Returns:
            User's contact ID, which we save in our user model.

        """
        pass

    @abstractmethod
    def add_tag_to_contact(self, user, tag):
        pass

    @abstractmethod
    def remove_tag_from_contact(self, user, tag) -> bool:
        pass


class ActiveCampaignService(EmailAutomationService):
    client: Optional[ActiveCampaignClient] = None

    def __init__(self, provider: EmailAutomationProvider):
        super().__init__(provider)
        # At startup, create the appropriate client for the email automation service
        # based on the Django settings.
        self.client = ActiveCampaignClient(provider.api_url, provider.api_key)

    def get_contact_id(self, email) -> str:
        """
        If a user exists in the external service, get the ID for that user.

        Args:
            email:       Email of user on our system

        Returns:
            Integer ID of user in remote system, cast to a string.
        """

        if not email:
            raise ValueError("email argument is required")

        try:
            response = self.client.get_contact(email)
        except Exception as e:
            raise Exception(
                f"Could not get contact information from ActiveCampaign for email {email}"
            ) from e

        if not isinstance(response, dict):
            # We expect a JSON response from email automation service, which Django should
            # resolve into a dictionary. So if we get something else, something went wrong.
            # TODO: Make this more abstract for other types of external services.
            logger.exception(
                f"get_contact_id() Unexpected response from remote service getting contact ID: {response}"
            )
            raise Exception(
                f"Could not get contact information from ActiveCampaign for email {email}"
            )

        errors = response.get("errors")
        if errors:
            logger.exception(f"get_contact_id() Errors : {errors}")
            raise Exception(
                f"Could not get contact information from ActiveCampaign for email {email}"
            )

        try:
            contacts = response.get("contacts")
            if contacts and len(contacts) > 0:
                contact = contacts[0]
                contact_id = contact.get("id", None)
                if contact_id:
                    contact_id = int(contact_id)
                    logger.info(f"Found id {contact_id} for user email {email}")
                    return str(contact_id)
        except Exception as e:
            logger.exception("get_contact_id() Could not get id from response")
            raise Exception(
                f"Could not get contact information from ActiveCampaign"
                f" for email {email}"
            ) from e

    def add_contact(self, 
                    user, 
                    authorized_email: str = None) -> Optional[str]:
        """
        Adds a contact to email automation service. If one already
        exists this method will sync our model to the latest data
        (e.g. identifier) in the remote email automation service.

        The reason we ask for the authorized email as an argument
        (and don't just use the email associated with 'user') is because
        each user can have multiple emails defined by Allauth.
        So we want to allow the caller to say exactly which email to use.

        But if authorized_email isn't provided, we'll just use
        the default EmailAddress associated with user.

        Args:
            user:                   A User object.
            authorized_email:       Email authorized by Allauth

        Returns:
            User's contact ID, which we save in our user model.

        Raises:
            ValueError:             If user is not provided.
            Exception:              If there was an error creating the contact.

        """

        if not user:
            raise ValueError("user argument is required")
        if authorized_email:
            # Make sure this email is valid for this user...
            try:
                ea: EmailAddress = EmailAddress.objects.get_for_user(
                    user=user, email=authorized_email
                )
                if not ea:
                    raise Exception(
                        f"User {user} does not have a registerd email {authorized_email}"
                    )
            except EmailAddress.DoesNotExist:
                raise Exception(
                    f"User {user} does not have email {authorized_email} authorized"
                )
        else:
            try:
                ea: EmailAddress = EmailAddress.objects.get_primary(user)
                if not ea:
                    raise Exception(
                        f"User {user} does not have a primary email authorized"
                    )
            except EmailAddress.DoesNotExist:
                raise Exception(f"User {user} does not have a primary email authorized")

        email = ea.email
        logger.debug(
            f"Registering user {user} and email {email} "
            f"with email automation service"
        )

        data = {
            "contact": {"email": email, "first_name": user.informal_name}
        }
        try:
            response = self.client.create_contact(data)
            if isinstance(response, str):
                raise Exception(f"Response was not correct: {response}")
        except Exception:
            logger.exception("Couldn't create user on email automation service")
            return None

        errors = response.get("errors")
        if errors:
            for error in errors:
                code = error.get("code")
                if code == "duplicate":
                    logger.warning(
                        f"Tried to create user {user}on email automation "
                        f"service but user already existed"
                    )
                    return None
            raise Exception("Couldn't create user on email automation service")

        try:
            ac_id = response["contact"]["id"]
            if not ac_id:
                logger.exception("Couldn't find AC id in response")
                return None
        except KeyError:
            raise Exception("Didn't get contact id back from email automation service when creating user")

        logger.info(
            f"SUCCESS: Created email automation service user for "
            f"user {user.email} with ac_id {ac_id}"
        )
        return ac_id

    def add_tag_to_contact(self, user, tag) -> bool:
        """
        Add a tag to a contact. If we don't have a tag ID, we'll first
        create it in the service and then add it to the contact.
        """

        if not hasattr(self.provider, "tag_ids") or self.provider.tag_ids is None:
            self.provider.tag_ids = {}
        try:
            tag_id = self.provider.tag_ids.get(tag, None)
        except Exception:
            tag_id = None

        if not tag_id:
            # See if it exists in AC bc we don't have it locally
            tag_list: Dict[str, int] = self.client.list_tags()
            tag_id = tag_list.get(tag, None)
            if tag_id:
                # Tag exists in AC, so add it to our local tag_ids dictionary.
                self.provider.tag_ids[tag] = tag_id
                self.provider.save()

        if not tag_id:
            # Tag doesn't exist locally or in AC, so create it
            try:
                tag_id = self.client.create_tag(tag)
                self.provider.tag_ids[tag] = tag_id
                self.provider.save()
            except Exception:
                logger.exception(
                    f"Could not create new tag {tag} in email automation service."
                )
                return False

        try:
            self.client.add_a_tag_to_contact(
                ac_user_id=user.email_automation_provider_user_id, tag_id=tag_id
            )
        except Exception as e:
            logger.exception(
                f"Couldn't add email automation provider tag {tag} to user {user}"
            )
            raise e
        return True

    def get_tags_for_contact(self, user) -> List[str]:
        """
        Get a list of tags applied to a user.
        """
        try:
            tags_data = self.client.get_tags_for_contact(
                ac_user_id=user.email_automation_provider_user_id
            )
            contact_tags = tags_data["contactTags"]
        except Exception:
            logger.exception(f"Couldn't get list of tags for user {user}")
            return []

        # Note that 'id' is the contact_tag (association). 'tag' is the actual tag id.
        tag_ids = [tag_data["tag"] for tag_data in contact_tags]

        # Do a reverse lookup on our tag_ids dictionary to get the tag names.
        tags = []
        for tag_id in tag_ids:
            for tag, tag_id_ in self.provider.tag_ids.items():
                if tag_id == tag_id_:
                    tags.append(tag)

        return tags

    def remove_tag_from_contact(self, user, tag) -> bool:
        """
        Removes a tag from a user.

        Returns:
            True if tag was removed, False otherwise.
        """

        try:
            tag_id = self.provider.tag_ids[tag]
        except Exception:
            logger.exception(
                "Could not find tag id for tag {tag} in email automation provider's"
                "tag definitions"
            )
            return False

        try:
            self.client.remove_a_tag_from_contact(
                ac_user_id=user.email_automation_provider_user_id, tag_id=tag_id
            )
        except Exception:
            logger.exception(
                f"Couldn't remove email automation provider tag {tag} to user {user}"
            )
            return False

        return True

    def test_api_connection(self) -> bool:
        """
        Test the ActiveCampaign API connection.
        """
        return self.client.test_api_connection()
