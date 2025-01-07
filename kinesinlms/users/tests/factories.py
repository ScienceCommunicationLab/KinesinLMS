from collections.abc import Sequence
from typing import Any

from django.contrib.auth.models import Group
from factory import Faker, SelfAttribute, post_generation
from factory.django import DjangoModelFactory

from kinesinlms.users.models import (
    CareerStageType,
    GenderType,
    GroupTypes,
    User,
    UserSettings,
)


class GroupFactory(DjangoModelFactory):
    class Meta:
        model = Group


class UserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    enable_badges = True


class UserFactory(DjangoModelFactory):
    username = Faker("user_name")
    email = Faker("email")
    name = Faker("name")
    informal_name = f"{SelfAttribute('name')}ito"
    is_staff = False
    # is_test_user is used when we have test users
    # using the live site (we set to true, so we can filter out
    # from 'real' data)...this does
    # not have to do with test framework.
    is_test_user = False

    career_stage = CareerStageType.DOCTORATE
    gender = GenderType.MALE.name
    gender_description = "Some gender description..."
    year_of_birth = 1970
    why_interested = "I'm building it."
    agree_to_honor_code = True

    # Don't create settings, it's created via a signal.

    @post_generation
    def password(self, create: bool, extracted: Sequence[Any], **kwargs):  # noqa: FBT001
        password = (
            extracted
            if extracted
            else Faker(
                "password",
                length=42,
                special_chars=True,
                digits=True,
                upper_case=True,
                lower_case=True,
            ).evaluate(None, None, extra={"locale": None})
        )
        self.set_password(password)

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """Save again the instance if creating and at least one hook ran."""
        if create and results and not cls._meta.skip_postgeneration_save:
            # Some post-generation hooks ran, and may have modified us.
            instance.save()

    class Meta:
        model = User
        django_get_or_create = ["{{cookiecutter.username_type}}"]


class EducatorFactory(UserFactory):
    """
    Creates a user that belongs to the EDUCATOR group.
    """

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        super()._after_postgeneration(instance, create, results)
        group = Group.objects.get(name=GroupTypes.EDUCATOR.name)
        instance.groups.add(group)
        instance.save()
