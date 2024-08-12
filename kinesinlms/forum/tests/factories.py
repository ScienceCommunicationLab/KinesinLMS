import factory

from kinesinlms.core.constants import ForumProviderType
from kinesinlms.forum.models import CourseForumGroup, CohortForumGroup, ForumCategory, ForumSubcategory, \
    ForumTopic, ForumProvider


class CourseForumGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourseForumGroup


class FormCohortGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CohortForumGroup


class ForumCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ForumCategory


class ForumSubcategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ForumSubcategory


class ForumTopicFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ForumTopic


class ForumProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ForumProvider

    type = ForumProviderType.DISCOURSE.name
    forum_url = "http://localhost:3000"
    active = True
    forum_api_username = "admin"
    enable_sso = True
