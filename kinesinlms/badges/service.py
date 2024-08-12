"""
Service classes for Badges.

This module also contains an async Celery task method,
(rather than in a separate tasks.py file, which causes circular imports).
"""

import logging
from typing import Tuple

import requests
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from rest_framework.status import HTTP_401_UNAUTHORIZED, HTTP_200_OK, HTTP_201_CREATED

from kinesinlms.badges.models import BadgeAssertion, BadgeProviderType, BadgeAssertionCreationStatus
from kinesinlms.badges.models import BadgeClass
from kinesinlms.badges.models import BadgeProvider

logger = logging.getLogger(__name__)

User = get_user_model()


class BadgeCreationException(Exception):
    pass


class BaseBadgeServiceError(Exception):
    pass


class APITokenNotValidException(Exception):
    pass


class BaseBadgeService:
    """
    Abstract class for external badge services.
    Defines methods for accessing a badge provider,
    mainly to generate badge assertions.
    """

    def create_remote_badge_assertion(self, badge_assertion: BadgeAssertion) -> bool:
        raise NotImplementedError()

    def refresh_token(self) -> str:
        raise NotImplementedError()

    def retry_badge_assertion(self, badge_assertion: BadgeAssertion) -> bool:
        raise NotImplementedError()

    def issue_badge_assertion(self, badge_class: BadgeClass, recipient, do_async: bool = True) -> BadgeAssertion:
        """
        Create a local and remote BadgeAssertion for a recipient who achieved the required
        criteria for a particular BadgeClass.

        This method
        - creates a BadgeAssertion locally for a recipient who just earned it.
        - tries to create badge in remote service, either directly in process or via an async task

        If the call to the remote service is successful, it should provide an open_badge_id url
        pointing to the external badge assertion for this user.

        Note that we return the local BadgeAssertion immediately while launching an async task for the
        request/response to the external service.

        Args:
            badge_class:    The BadgeClass that the recipient has earned
            recipient:      The user who has earned the badge
            do_async:       If True, the request to the external service will be made asynchronously.

        Returns:
            The BadgeAssertion instance that was created locally.

        """

        if badge_class.provider.type != BadgeProviderType.BADGR.name:
            raise Exception(f"BadgeService: Not configured to send a badge assertion request "
                            f"to {badge_class.provider}. Only BADGR is supported at the moment.")

        logger.debug(f"BadgeService: Starting request to {badge_class.provider} to "
                     f"create a new assertion for recipient: {recipient} "
                     f"badge class: {badge_class} ")

        badge_assertion, created = BadgeAssertion.objects.get_or_create(badge_class=badge_class,
                                                                        recipient=recipient)
        if not created:
            logger.warning(f"User {recipient} already had badge assertion for "
                           f"badge_class {badge_class}. Updating with new one ")
            if badge_assertion.creation_status == BadgeAssertionCreationStatus.COMPLETE.name:
                logger.warning(f"Badge assertion for {recipient} and {badge_class} is already complete.")
                return badge_assertion

            elif badge_assertion.creation_status == BadgeAssertionCreationStatus.IN_PROGRESS.name:
                logger.warning(f"Badge assertion for {recipient} and {badge_class} is already in progress.")
                return badge_assertion

            elif badge_assertion.creation_status == BadgeAssertionCreationStatus.FAILED.name:
                logger.warning(f"Badge assertion for {recipient} and {badge_class} has failed. Retrying...")
                badge_assertion.clear()

            elif badge_assertion.creation_status == BadgeAssertionCreationStatus.STAGED.name:
                # If it's already staged, we're ok to start the process.
                pass

        badge_assertion.creation_status = BadgeAssertionCreationStatus.STAGED.name
        badge_assertion.issued_on = now()
        badge_assertion.save()

        if do_async:
            from kinesinlms.badges.tasks import create_external_badge_assertion_task
            create_external_badge_assertion_task.apply_async(args=[],
                                                             kwargs={'badge_assertion_id': badge_assertion.id},
                                                             # Use countdown to make sure DB transaction went through
                                                             # before starting task...
                                                             countdown=5)
        else:
            self.create_remote_badge_assertion(badge_assertion)

        return badge_assertion


class BadgrBadgeService(BaseBadgeService):
    """
    Encapsulates logic to gain access to, and create badge assertions in,
    the Badgr external badge service.

    On __init__, this class requires an instance of a BadgeProvider
    that has been set up to include access information for Badgr.

    To create a badge, this class requires that a badge class for the intended
    assertion has  already been created remotely in Badgr, and a BadgeClass instance
    has been set up to hold that information and is provided in the method call.

    """

    def __init__(self, badge_provider: BadgeProvider):
        if not badge_provider:
            raise Exception("Must configure provider")
        self.badge_provider = badge_provider

    def create_remote_badge_assertion(self, badge_assertion: BadgeAssertion) -> bool:
        """
        Create a badge assertion to reflect our local BadgeAssertion.
        As part of this process, refresh the remote service API token if it's gone stale.

        IMPORTANT: the BadgeAssertion instance's state is updated with the
        result of the remote assertion creation.

        Args:
            badge_assertion     An instance of a BadgeAssertion model representing student's achievement

        Returns:
            Boolean flag indicating whether remote assertion was created or not.
            (Return info will be stored in BadgeAssertion)

        """
        success = True
        badge_provider: BadgeProvider = badge_assertion.badge_class.provider

        # Make sure we have access to remote service...
        if not badge_provider.access_token:
            try:
                # Use the BADGR username and email stored in the environment
                # to get an access token.
                # TODO: Figure out problems with Badgr refresh token.
                #       Then use API key and refresh token here instead
                #       of creating new key/refresh token pair each time.
                self.create_new_provider_tokens(badge_provider)
            except Exception:
                logger.exception("Error creating badge assertion")
                badge_assertion.error_message = "Error creating badge assertion."
                badge_assertion.save()
                success = False
                return success

        # Create badge assertion...
        try:
            self._create_badge_assertion(badge_assertion)
            badge_assertion.creation_status = BadgeAssertionCreationStatus.COMPLETE.name
        except APITokenNotValidException:
            # Create a new access token and try again
            self.create_new_provider_tokens(badge_provider)
            try:
                self._create_badge_assertion(badge_assertion)
            except APITokenNotValidException as api_e:
                error_message = f"Could not get valid token to access Badgr API. : {api_e}"
                logger.error(error_message)
                badge_assertion.creation_status = BadgeAssertionCreationStatus.FAILED.name
                badge_assertion.error_message = error_message
                success = False
        except BaseBadgeServiceError as ebs_e:
            logger.error(f"Error creating badge assertion: {ebs_e}")
            badge_assertion.creation_status = BadgeAssertionCreationStatus.FAILED.name
            badge_assertion.error_message = "Error creating badge assertion."
            success = False
        except Exception:
            logger.exception("Error creating badge assertion")
            badge_assertion.creation_status = BadgeAssertionCreationStatus.FAILED.name
            badge_assertion.error_message = "Error creating badge assertion."
            success = False

        badge_assertion.save()

        return success

    def create_new_provider_tokens(self, badge_provider: BadgeProvider):
        try:
            access_token, refresh_token = self.create_tokens()
            badge_provider.access_token = access_token
            badge_provider.refresh_token = refresh_token
            badge_provider.save()
        except Exception:
            error_message = "Could not update provider tokens"
            logger.exception(error_message)
            raise BaseBadgeServiceError(error_message)

    def create_tokens(self) -> Tuple[str, str]:
        """
        Create a new access token using our Badgr user credentials.
        We should be using the refresh token, but it's not working
        quite right. While we wait for direction from Badgr, we're
        going to use this method, which just creates a completely
        new access token (and refresh token) using our account credentials.

        If the POST request is successful, the response from Badgr will look like this:
            {
                "access_token": "nPI0lLB0z7hsbjOw2MHXKvI5Sy9B8i",
                "expires_in": 86400,
                "token_type": "Bearer",
                "scope": "rw:profile rw:issuer rw:backpack",
                "refresh_token": "6sZK2v8pTGm6Ur7psJlGMalktw1dm6"
            }

        Returns:
            A new access_token and refresh_token

        """
        token_url = f"{self.badge_provider.api_url}o/token"
        params = {
            "username": self.badge_provider.username,
            "password": self.badge_provider.password
        }
        r = None
        try:
            r = requests.post(token_url, data=params)
            if not r or r.status_code != HTTP_200_OK:
                raise Exception()
        except Exception:
            error_message = "Could not create Badgr token."
            if r:
                error_message += f"Response status code: {r.status_code}"
            logger.exception(f"create_tokens(): {error_message}")
            raise Exception(error_message)

        try:
            badgr_credentials = r.json()
            access_token = badgr_credentials['access_token']
            refresh_token = badgr_credentials['refresh_token']
        except Exception as e:
            error_message = "Could not read response from Badgr"
            logger.exception(f"create_tokens(): {error_message}")
            raise Exception(error_message) from e

        return access_token, refresh_token

    def refresh_token(self) -> str:
        """
        Refresh the Badgr API access_token using the Badgr refresh key.

        NOTE:
        This process isn't quite working right, and looking to Badgr for
        help, so at the moment I'm not using this method.
        Instead, I just call create_tokens() to create a whole new
        token/refresh token pair each time.

        Returns:
            A new access_token

        Raises:
            Exception if token cannot be refreshed

        """
        token_refresh_url = f"{self.badge_provider.api_url}o/token"
        # No headers needed for this operation
        headers = {}
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.badge_provider.refresh_token,
            # Per Badgr support...have to include client_id and client_secret:
            "client_id": "public",
            "client_secret": ""
        }
        r = None
        try:
            r = requests.post(token_refresh_url, headers=headers, data=data)
            if not r or r.status_code != HTTP_200_OK:
                raise Exception()
        except Exception:
            error_message = "Could not refresh Badgr token."
            if r:
                error_message += f"Response status code: {r.status_code}"
            logger.exception(error_message)
            raise Exception(error_message)

        data = r.json()
        new_access_token = data['access_token']
        return new_access_token

    def _create_badge_assertion(self, badge_assertion: BadgeAssertion) -> str:
        """
        Create a Badge Assertion in remote Badgr service.

        Args:
            badge_assertion         A BadgeAssertion instance representing the new badge assertion

        Returns:
            badge_image_url         URL for new badge image representing assertion.

        Raises:
            APITokenNotValidException           If the access_token is no longer valid
            BadgeCreationException              For any other kind of exception

        """
        entity_id = badge_assertion.badge_class.external_entity_id

        access_token = badge_assertion.badge_class.provider.access_token
        if not access_token:
            raise BadgeCreationException(f"access_token is not set on "
                                         f"BadgeProvider: {badge_assertion.badge_class.provider}")

        badge_assertion_url = f"{self.badge_provider.api_url}v2/badgeclasses/{entity_id}/assertions"
        salt = self.badge_provider.salt

        logger.info(f"Sending request to Badgr to issue assertion for "
                    f"badge assertion : {badge_assertion}...")

        headers = {
            'Authorization': f"Bearer {access_token}",
            'Content-type': 'application/json',
        }
        data = {
            'recipient': {
                'identity': badge_assertion.recipient.email,
                'hashed': True,
                'type': 'email',
                'salt': salt
            }
        }

        r = requests.post(badge_assertion_url, headers=headers, json=data)
        if r.status_code == HTTP_401_UNAUTHORIZED:
            raise APITokenNotValidException()
        elif r.status_code != HTTP_201_CREATED:
            logger.error(f"Badgr did not create badge assertion. Status code: {r.status_code} content: {r.content}")
            raise BadgeCreationException(f"Invalid response from Badgr: {r.status_code}")

        logger.info(f"Successfully created badge assertion on Badgr. "
                    f" status code : {r.status_code} "
                    f" content {r.content}")
        data = r.json()

        assertion_json = data['result'][0]
        open_badge_id = assertion_json.get('openBadgeId', None)
        entity_id = assertion_json.get('entityId', None)
        badge_image_url = assertion_json.get('image', None)

        if not open_badge_id:
            error_message = "Created badge assertion in Badgr but no openBadgeId was returned!"
            raise BadgeCreationException(error_message)

        logger.info(f"  - Open badge ID for badge assertion: {open_badge_id}")
        badge_assertion.open_badge_id = open_badge_id
        badge_assertion.external_entity_id = entity_id
        badge_assertion.badge_image_url = badge_image_url
        badge_assertion.save()
        return badge_image_url

    def retry_badge_assertion(self, badge_assertion: BadgeAssertion) -> bool:
        """
        Retry a failed badge assertion.

        Args:
            badge_assertion     The BadgeAssertion instance to retry

        Returns:
            True if the retry async process was successfully started, false if not.
        """
        if badge_assertion.creation_status == BadgeAssertionCreationStatus.COMPLETE.name:
            logger.warning("Badge assertion is complete. Cannot retry")
            return False
        from kinesinlms.badges.tasks import create_external_badge_assertion_task
        create_external_badge_assertion_task.apply_async(args=[],
                                                         kwargs={'badge_assertion_id': badge_assertion.id},
                                                         # Use countdown to make sure DB transaction went through
                                                         # before starting task...
                                                         countdown=5)
