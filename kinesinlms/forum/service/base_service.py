import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple

from django.contrib.auth import get_user_model
from requests.exceptions import HTTPError

from kinesinlms.course.models import Course

logger = logging.getLogger(__name__)
User = get_user_model()


# EXCEPTIONS
# ~~~~~~~~~~~~~~~~~~~


class ForumServiceError(HTTPError):
    """ A generic error while attempting to communicate with Discourse """


class ForumAPIFailed(Exception):
    """
    The call to Discourse API failed to connect to discourse.
    """
    pass


class ForumAPIUnsuccessful(Exception):
    """
    The API call went through ok but success != "OK"
    """
    pass


class ForumItemAlreadyExists(Exception):
    pass


class BaseForumService(ABC):

    def __init__(self, provider: 'kinesinlms.forum.models.ForumProvider'):
        if not provider:
            raise ValueError("provider argument is required")
        self.provider = provider

    @abstractmethod
    def is_course_forum_configured(self, course) -> bool:
        pass

    # ~~~~~~~~~~~~~~~~~~~
    # GROUPS
    # ~~~~~~~~~~~~~~~~~~~

    # Groups should be defined before categories and subcategories
    # as we need to establish group permissions, which are then
    # used when creating new category and subcategories.
    @abstractmethod
    def get_or_create_course_forum_group(self, course) \
            -> Tuple["kinesinlms.forum.models.CourseForumGroup", bool]:
        pass

    @abstractmethod
    def get_or_create_cohort_forum_group(self, cohort) \
            -> Tuple['kinesinlms.forum.models.CohortForumGroup', bool]:
        pass

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # CATEGORIES & SUBCATEGORIES
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @abstractmethod
    def get_or_create_forum_category(self, course) \
            -> Tuple['kinesinlms.forum.models.ForumCategory', bool]:
        pass

    @abstractmethod
    def delete_forum_category(self, course, delete_model: bool = True) -> bool:
        pass

    @abstractmethod
    def get_or_create_forum_subcategory(self,
                                        forum_category: 'kinesinlms.forum.models.ForumCategory',
                                        subcategory_type: str,
                                        cohort_forum_group: Optional['kinesinlms.forum.models.CohortForumGroup'] = None,
                                        ensure_unique_name: bool = False) \
            -> Tuple['kinesinlms.forum.models.ForumSubcategory', bool]:
        pass

    @abstractmethod
    def delete_forum_subcategory_for_course(self,
                                            course,
                                            delete_local_model=True) -> bool:
        pass

    @abstractmethod
    def delete_forum_subcategory_for_cohort_forum_group(self,
                                                        cohort_forum_group: 'kinesinlms.forum.models.CohortForumGroup',
                                                        delete_all_topics=True,
                                                        delete_model=True) -> bool:
        pass

    # ~~~~~~~~~~~~~~~~~~~
    # TOPICS
    # ~~~~~~~~~~~~~~~~~~~

    @abstractmethod
    def create_or_update_forum_topic(self,
                                     discussion_block: 'kinesinlms.learning_library.models.Block',
                                     course: 'kinesinlms.course.models.Course') -> List['kinesinlms.forum.models.ForumTopic']:
        pass

    @abstractmethod
    def create_topic(self,
                     discussion_block: 'kinesinlms.learning_library.models.Block',
                     course: Course,
                     forum_subcategory: 'kinesinlms.forum.models.ForumSubcategory',
                     topic_title: str = None) -> 'kinesinlms.forum.models.ForumTopic':
        pass

    @abstractmethod
    def update_topic(self,
                     forum_topic: 'kinesinlms.forum.models.ForumTopic',
                     title: str = None,
                     html_content: str = None) -> bool:
        pass

    @abstractmethod
    def delete_topic(self, forum_topic: 'kinesinlms.forum.models.ForumTopic') -> bool:
        pass

    @abstractmethod
    def user_can_view_topic(self, forum_topic, user) -> bool:
        pass

    @abstractmethod
    def get_topic_posts(self, topic_id: int) -> List[dict]:
        pass

    @abstractmethod
    def topic_url(self, forum_topic: 'kinesinlms.forum.models.ForumTopic') -> Optional[str]:
        pass

    # ~~~~~~~~~~~~~~~~~~~
    # CALLBACKS
    # ~~~~~~~~~~~~~~~~~~~

    @abstractmethod
    def read_forum_callback(self, request) -> Dict:
        pass

    @abstractmethod
    def save_forum_callback(self, json_data: Dict):
        pass

    # ~~~~~~~~~~~~~~~~~~~
    # USERS
    # ~~~~~~~~~~~~~~~~~~~
    @abstractmethod
    def add_user_to_group(self, group_id: int, username: str):
        pass

    @abstractmethod
    def remove_user_from_group(self, group_id: int, username: str):
        pass

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # SSO METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @abstractmethod
    def sso_validate(self, payload, signature, secret):
        pass

    @abstractmethod
    def sso_payload(self, secret, **kwargs):
        pass

    @abstractmethod
    def sso_redirect_url(self, nonce, secret, user, **kwargs):
        pass

    @abstractmethod
    def sync_discourse_sso_user(self, user):
        pass

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # COMPLETE
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # TODO: Make these abstract and therefore required?

    def configure_forum_for_new_course(self, course: Course):
        pass

    def populate_cohort_forum_group_with_subcategory_and_topics(self,
                                                                cohort_forum_group: 'kinesinlms.forum.models.CohortForumGroup'):
        pass

    def delete_all_discourse_items_for_course(self, course: Course):
        pass

    def user_can_create_topic(self, user: User, forum_topic: 'kinesinlms.forum.models.ForumTopic') -> bool:
        pass
