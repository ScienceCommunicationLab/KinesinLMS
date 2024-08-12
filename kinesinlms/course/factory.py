import logging

from django.contrib.auth.models import Group

from kinesinlms.course.models import CourseNode, Course, Cohort, CohortType

logger = logging.getLogger(__name__)


class CourseFactory:
    """
    This is a propery factory for creating courses, not for creating dummy courses in tests.
    """

    @classmethod
    def create(cls, create_course_root_node: bool = True, **kwargs):
        """
        Set up a course and related services that derive from the course,
        for example a Django group or Discourse forum.

        We use a factory method rather than a Manager, as the Manager approach causes
        recursive imports.

        Args:
            create_course_root_node     Boolean flag indicating whether to create a root CourseNode
                                        for this course.
                                        We want to do this when testing, but don't want to do this
                                        when creating a course from the serializer.

        """

        course: Course = Course.objects.create(**kwargs)

        # Create the course root node
        course_slug = kwargs['slug']
        course_run = kwargs['run']
        root_node_slug = f"{course_slug}_{course_run}".lower()  # by convention
        root_node_display_name = root_node_slug.upper()  # by convention
        if create_course_root_node:
            course_root_node = CourseNode.objects.create(slug=root_node_slug,
                                                         display_name=root_node_display_name)
            logger.debug(f"Created CourseNode {course_root_node}")
            course.course_root_node = course_root_node

        course.save()
        logger.debug(f"Created Course {course}")

        # DJANGO GROUP
        # Make sure a Django group exists for this course
        group, group_created = Group.objects.get_or_create(name=course.course_group_name)
        if group_created:
            logger.debug(f"Created Django group {group} for course {course}")

        # DEFAULT COHORT
        # Make sure the 'default' cohort exists
        try:
            default_cohort, default_cohort_created = Cohort.objects.get_or_create(course=course,
                                                                                  name="Default cohort",
                                                                                  slug=CohortType.DEFAULT.name,
                                                                                  type=CohortType.DEFAULT.name)
        except Exception as e:
            logger.exception("Could not create Cohort object")
            raise e

        if default_cohort_created:
            logger.debug(f"Created 'default' cohort {default_cohort} for course {course}")

        return course
