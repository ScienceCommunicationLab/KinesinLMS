import logging
from typing import List, Dict

import requests

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ACTIVECAMPAIGN METHODS AND CLASSES
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

logger = logging.getLogger(__name__)


class NoActiveCampaignTagIDDefined(Exception):
    pass


class ActiveCampaignClient(object):
    """
    Communicates with the ActiveCampaign API.

    This class should be a thin layer over the AC API.
    Operations that have a bit more logic should be
    implemented in the ActiveCampaignService class.

    """
    BASE_URL = '{}/api/3'

    def __init__(self, url, api_key):
        self.BASE_URL = self.BASE_URL.format(url)
        self.API_KEY = api_key

    # ~~~~~~~~~~~~~~~~~~~~~
    # PUBLIC METHODS
    # ~~~~~~~~~~~~~~~~~~~~~

    def test_api_connection(self) -> bool:
        """
        Test the connection to the ActiveCampaign API.
        """
        result = self.list_users()
        if result and 'users' in result:
            return True
        return False

    def list_users(self):
        return self._get("/users")

    def get_contact(self, email: str) -> List:
        return self._get(f"/contacts/?search={email}")

    def create_contact(self, data):
        return self._post("/contact/sync", json=data)

    def list_tags(self) -> Dict[str, int]:
        """
        List tag names and IDs for all tags defined in AC.

        Returns:
            Dictionary of tag names (key) and IDs (value)
        """

        result = self._get("/tags")

        try:
            tags_data = result['tags']
        except Exception as e:

            raise Exception(f"Could not get list of tag in ActiveCampaign.") from e

        tag_data = {tag_data['tag']: tag_data['id'] for tag_data in tags_data}

        return tag_data

    def create_tag(self, tag: str, description: str = None) -> str:
        """
        Creates a 'contact' tag in ActiveCampaign.

        Returns:
            The ID of the tag that was created.
        """

        data = {
            "tag": {
                "tag": tag,
                "tagType": "contact",
                "description": description
            }
        }
        result = self._post("/tags", json=data)

        if result.status_code != 201:
            raise Exception(f"Could not create tag {tag} in ActiveCampaign. "
                            f"Status code: {result.status_code} "
                            f"Response: {result.content}")

        tag_id = result['tag']['id']

        return tag_id

    def add_a_tag_to_contact(self, ac_user_id: str, tag_id: str):
        data = {
            "contactTag": {
                "contact": f"{ac_user_id}",
                "tag": tag_id
            }
        }
        return self._post("/contactTags", json=data)

    def remove_a_tag_from_contact(self, ac_user_id: str, tag_id: str) -> bool:
        """
        The ActiveCampaign API is really clumsy. In order to remove a tag,
        we have to:
            - call the API to get the Tag's ID based on the string
            - call the API to get all tags associated with user, in order to get the
              "association" id that maps the current tag ot the user
            - call the API to delete this association.
        """

        # get association id
        user_contact_tags = self._get(f"/contacts/{ac_user_id}/contactTags")
        contact_tags = user_contact_tags['contactTags']

        contact_tag_id = None
        for contact_tag in contact_tags:
            if contact_tag['tag'] == tag_id:
                contact_tag_id = contact_tag['id']
                break

        if contact_tag_id:
            result = self._delete(f"/contactTags/{contact_tag_id}")
            logger.info(f"Deleted contact tag id: {contact_tag_id} "
                        f"for user {ac_user_id}. "
                        f"result: {result}")
            return True

        return False

    def get_tags_for_contact(self, ac_user_id: str) -> List[str]:
        """
        Get a list of tag IDs applied to a user
        """
        return self._get(f"/contacts/{ac_user_id}/contactTags")

    # ~~~~~~~~~~~~~~~~~~~~~
    # PRIVATE METHODS
    # ~~~~~~~~~~~~~~~~~~~~~

    def _get(self, endpoint, **kwargs):
        return self._request('GET', endpoint, **kwargs)

    def _post(self, endpoint, **kwargs):
        return self._request('POST', endpoint, **kwargs)

    def _put(self, endpoint, **kwargs):
        return self._request('PUT', endpoint, **kwargs)

    def _delete(self, endpoint, **kwargs):
        return self._request('DELETE', endpoint, **kwargs)

    def _request(self, method, endpoint, headers=None, **kwargs):
        _headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Api-Token': self.API_KEY
        }
        if headers:
            _headers.update(headers)

        return self._parse(requests.request(method, self.BASE_URL + endpoint, headers=_headers, **kwargs))

    def _parse(self, response):
        if 'application/json' in response.headers['Content-Type']:
            r = response.json()
        else:
            return response.text

        return r
