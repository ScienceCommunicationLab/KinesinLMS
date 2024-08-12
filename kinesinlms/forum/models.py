import logging
from enum import Enum

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from slugify import slugify

from kinesinlms.core.constants import ForumProviderType

logger = logging.getLogger(__name__)


class ForumActivityType(Enum):
    TOPIC = "topic"
    POST = "post"


class ForumProvider(models.Model):
    site = models.OneToOneField(Site,
                                related_name='forum_provider',
                                on_delete=models.CASCADE)

    type = models.CharField(max_length=30,
                            blank=False,
                            default=ForumProviderType.DISCOURSE.name,
                            choices=[(item.name, item.value) for item in ForumProviderType],
                            help_text=_("Type of forum utilized for this site."))

    forum_url = models.URLField(blank=True,
                                null=True,
                                help_text=_("URL of the forum server "
                                            "for this site, if available."))

    active = models.BooleanField(default=False,
                                 null=False,
                                 help_text=_("Enable forums for this site."))

    forum_api_username = models.CharField(max_length=100,
                                          blank=True,
                                          null=True,
                                          help_text=_("API username for the forum server "
                                                      "for this site, if available."))

    # SSO might only be available for certain forum providers...e.g. Discourse
    enable_sso = models.BooleanField(default=True,
                                     blank=False,
                                     null=False,
                                     help_text=_("Enable SSO for this external forum server"))

    @property
    def api_key(self) -> str:
        """
        API key for the forum server for this site, if available
        """
        return settings.FORUM_API_KEY

    @property
    def sso_secret(self) -> str:
        """
        SSO secret for the forum server for this site, if available.
        Sensitive, so these are stored as env variables.
        """
        return settings.FORUM_SSO_SECRET

    @property
    def forum_callback_secret(self) -> str:
        """
        SSO callback secret for the forum server for this site, if available.
        Sensitive, so these are stored as env variables.
        """
        return settings.FORUM_WEBHOOK_SECRET

    def __str__(self):
        return f"Forum {self.id} for site {self.site}"


class CourseForumGroup(models.Model):
    """
    A forum group that contains all students in a course,
    regardless of cohort. This group is used to allow all students,
    to access certain subcategories regardless of cohort.
    """

    course = models.OneToOneField('course.Course',
                                  on_delete=models.CASCADE,
                                  related_name="course_forum_group",
                                  null=True,
                                  blank=True)

    group_id = models.IntegerField(null=False,
                                   blank=False)

    # Note: Discourse uses 'name' for groups as a primary key
    # in some API calls.
    name = models.CharField(max_length=200,
                            null=False,
                            blank=False)

    def __str__(self):
        return f"CourseForumGroup {self.group_id} {self.name}"


class CohortForumGroup(models.Model):
    """
    A simple model to keep track of forum cohort groups.

    One CohortForumGroup should always be created for the DEFAULT
    cohort in a course.

    After that, it's the course designer's decision on whether
    to dump all course cohorts into the same forum group, or
    to create a new CohortForumGroup for each cohort.

    Doing the latter is a bit tedious since, at least with Discourse,
    this means not just creating a new Discourse group for the cohort,
    but also creating a new subcategory and a copy of each topic to place
    in that new subcategory. This is currently the only way to limits topics
    to certain cohorts.

    "Wait, so where the link to a cohort?"

    To support both approaches described above, we have a many-to-one relationship
    between Cohort and CohortForumGroup. That way many Cohorts can be linked to
    a single CohortForumGroup.

    """

    course = models.OneToOneField('course.Course',
                                  on_delete=models.CASCADE,
                                  related_name="cohort_forum_groups",
                                  null=True,
                                  blank=True)

    is_default = models.BooleanField(default=True,
                                     null=False,
                                     blank=False)

    # ID of group in external forum service
    group_id = models.IntegerField(null=False,
                                   unique=True,
                                   blank=False)

    # Note: Discourse uses 'name' for groups as a primary key
    # in some API calls.
    name = models.CharField(max_length=200,
                            null=False,
                            blank=False)

    def __str__(self):
        return f"CohortForumGroup {self.group_id} {self.name}"


class ForumCategory(models.Model):
    """
    Links a forum category to a course slug and run:
    """

    class Meta:
        verbose_name_plural = "Forum categories"

    course = models.OneToOneField('course.Course',
                                  null=True,
                                  blank=False,
                                  on_delete=models.SET_NULL,
                                  related_name="forum_category")

    # ID of category in forum service
    category_id = models.IntegerField(null=True, blank=True)

    # Slug of category in forum service
    category_slug = models.SlugField(null=True, blank=True)

    def __str__(self):
        return f"({self.id}) ForumCategory ID {self.id} (category_id: {self.category_id} " \
               f"category_slug: {self.category_id})"

    @classmethod
    def generate_category_slug(cls, course_token: str) -> str:
        # NOTE:
        # - Discourse doesn't like underscores (removes them silently) but is ok with dashes.
        # - Discourse doesn't allow upper case slugs.
        return course_token.replace("_", "-").lower()


class ForumSubcategoryType(Enum):
    COHORT = "cohort"
    ALL_ENROLLED = "all_enrolled"


class ForumSubcategory(models.Model):
    """
    In the forum, we have a subcategory for each cohort in a course run.
    Each subcategory should be limited to the forum group representing
    that cohort.
    """

    class Meta:
        verbose_name_plural = "Forum subcategories"

    forum_category = models.ForeignKey(ForumCategory,
                                       null=False,
                                       blank=False,
                                       on_delete=models.CASCADE,
                                       related_name="forum_subcategories")

    type = models.CharField(max_length=50,
                            choices=[(tag.name, tag.value) for tag in ForumSubcategoryType],
                            default=None,
                            null=True,
                            blank=True)

    course_forum_group = models.OneToOneField(CourseForumGroup,
                                              null=True,
                                              blank=True,
                                              on_delete=models.SET_NULL,
                                              related_name="forum_course_subcategory")

    cohort_forum_group = models.OneToOneField(CohortForumGroup,
                                              null=True,
                                              blank=True,
                                              on_delete=models.SET_NULL,
                                              related_name="forum_cohort_subcategory")

    subcategory_id = models.IntegerField(null=True, blank=True, help_text="ID of subcategory in external forum service")

    subcategory_slug = models.SlugField(null=True, blank=True,
                                        help_text="Slug of subcategory in external forum service")

    @property
    def course_group(self):
        if self.type == ForumSubcategoryType.ALL_ENROLLED.name:
            return self.course_forum_group
        elif self.type == ForumSubcategoryType.COHORT.name:
            return self.cohort_forum_group
        else:
            logger.error(f"ForumSubcategory model {self} does not have a type set. ")

    # noinspection PyArgumentList
    def clean(self, *args, **kwargs):
        if type == ForumSubcategoryType.COHORT.name and not self.cohort_forum_group:
            raise ValidationError(f"ForumSubcategory of type {type} must have cohort_forum_group set")
        if type == ForumSubcategoryType.ALL_ENROLLED.name and not self.course_forum_group:
            raise ValidationError(f"ForumSubcategory of type {type} must have course_forum_group set")
        return super(ForumSubcategory, self).clean(*args, **kwargs)

    def __str__(self):
        return f"({self.id}) ForumSubcategory ID {self.id} (subcategory_id: {self.subcategory_id} " \
               f"subcategory_slug: {self.subcategory_slug})"

    @classmethod
    def generate_subcategory_name(cls,
                                  subcategory_type: str,
                                  name_suffix: str = None) -> str:
        """
        Simple method to generate a name for a subcategory in the forum.
        Creating as static method here so this procedure is defined in just one place.

        Discourse wants category names to be unique. There's an option to allow
        duplicate names but in local testing it doesn't seem to work. So let's just
        make category names unique for now by including course token text.

        Args:
            subcategory_type:
            name_suffix:           A suffix to add to the subcategory name

        Returns:
            A name for a subcategory
        """

        if subcategory_type not in [item.name for item in ForumSubcategoryType]:
            raise ValueError(f"subcategory_type {subcategory_type} is not valid.")

        if subcategory_type == ForumSubcategoryType.ALL_ENROLLED.name:
            subcategory_name: str = f"General Discussion"
        else:
            subcategory_name: str = f"Course Topics"

        # Add prefix for uniqueness
        if name_suffix:
            subcategory_name = f"{subcategory_name} ({name_suffix})"

        # If we add any other names in the future, make
        # sure they're not too long.
        # NOTE: Discourse disallows > 50 chars...
        if len(subcategory_name) > 50:
            logger.warning(f"truncating {subcategory_name} to max of 50 chars.")
            subcategory_name = subcategory_name[:50]

        return subcategory_name

    @classmethod
    def generate_subcategory_slug(cls,
                                  subcategory_type: str,
                                  course_token: str = None,
                                  cohort_group_name: str = None) -> str:
        """
        Simple method to generate a slug for a subcategory in forum.
        Creating as static method here so this procedure is defined in just one place.

        NOT: Return lowercase as Discourse only seems to like lowercase slugs.

        Args:
            subcategory_type:
            course_token:
            cohort_group_name:           A name for the discourse cohort group

        Returns:
            A slug for a subcategory
       """

        if subcategory_type == ForumSubcategoryType.ALL_ENROLLED.name:
            assert course_token, f"cohort_slug must be defined if subcategory_type {subcategory_type} "
            course_slug = ForumCategory.generate_category_slug(course_token)
            subcategory_slug = f"general-{course_slug}"
        else:
            assert cohort_group_name, f"cohort_group_name must be defined if subcategory_type {subcategory_type} "
            slug = slugify(cohort_group_name)
            subcategory_slug = f"topics-co-{slug}"

        subcategory_slug = subcategory_slug.replace("_", "-")
        return subcategory_slug.lower()


class ForumTopic(models.Model):
    """
    Links forum topics in course to a forum topic
    on the remote forum service. Forum topics are
    placed within a forum subcategory to limit them
    to students in a particular cohort, if required.

    Every course should have at least one cohort (the 'default'
    cohort), therefore every ForumTopic
    should be linked to at least one ForumSubcategory.

    If we didn't have cohorts, the Block <-> ForumTopic relationship
    would be a one-to-one (like Block <--> Assessment or Block <--> SIT ).
    """

    class Meta:
        unique_together = ('block', 'forum_subcategory')

    block = models.ForeignKey('learning_library.Block',
                              null=True,
                              blank=False,
                              on_delete=models.SET_NULL,
                              related_name="forum_topics")

    forum_subcategory = models.ForeignKey(ForumSubcategory,
                                          null=True,
                                          blank=False,
                                          on_delete=models.SET_NULL,
                                          related_name="forum_topics")

    topic_id = models.IntegerField(null=True,
                                   blank=True,
                                   help_text=_("ID of category in external forum service"))

    topic_slug = models.SlugField(null=True,
                                  blank=True,
                                  max_length=200,
                                  help_text=_("Slug of category in external forum service"))

    def title(self) -> str:
        if self.block:
            return self.block.display_name
        return ""

    def __str__(self):
        return f"({self.id}) ForumTopic ID {self.id} (topic_id: {self.topic_id} " \
               f"topic_slug: {self.topic_slug})"
