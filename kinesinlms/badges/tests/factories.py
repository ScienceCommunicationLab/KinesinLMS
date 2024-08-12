import factory.django
from django.conf import settings

from kinesinlms.badges.models import BadgeClass, BadgeClassType, BadgeProvider


class BadgeProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BadgeProvider
        django_get_or_create = ('slug',)

    site_id = 1
    api_url = "https://api.badgr.io/"
    name = "Badgr"
    slug = "BADGR"
    issuer_entity_id = getattr(settings, 'TEST_BADGE_PROVIDER_ISSUER_ID', None)
    salt = "12345"


class BadgeClassFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BadgeClass
        django_get_or_create = ('slug',)

    slug = "TEST_SP-course-passed"
    type = BadgeClassType.COURSE_PASSED.name
    name = "Test Course Passed"
    provider = factory.SubFactory(BadgeProviderFactory)
    description = "Student has finished the DEMO_SP Course."
    criteria = "Badge criteria would go here."

    @factory.post_generation
    def set_issuer_entity_id(self, create, extracted, **kwargs):   # noqa: F841
        """
        Expects the TEST_BADGE_PROVIDER_COURSE_BADGE_CLASS_ID env variable to be set
        with a valid badge class entity id pointing to a badge class on Badgr
        that should be awarded for passing the "test course"

        Args:
            create (_type_): _description_
            extracted (_type_): _description_
        """
        badge_class_entity_id = getattr(settings, 'TEST_BADGE_PROVIDER_COURSE_BADGE_CLASS_ID', None)
        if badge_class_entity_id:
            self.external_entity_id = badge_class_entity_id
            self.open_badge_id = f"https://api.badgr.io/public/badges/{badge_class_entity_id}"
            self.image_url = f"https://api.badgr.io/public/badges/{badge_class_entity_id}/image"
        else:
            self.external_entity_id = None
            self.open_badge_id = None
            self.image_url = None
        self.save()
