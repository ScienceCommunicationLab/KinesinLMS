import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from kinesinlms.badges.models import BadgeClass, BadgeClassType
from kinesinlms.badges.utils import get_badge_service
from kinesinlms.course.models import Course

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = "Generate 'missing' badge assertions for all users who have badges enabled and " \
           "have, in the past, passed a course that now awards badges."

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)

    def add_arguments(self, parser):
        parser.add_argument('--course', type=str, default='')
        parser.add_argument('--username', type=str, default='')

    def handle(self, *args, **options):
        course_token = options['course']
        username = options['username']
        User.objects.get(username=username)
        courses = []

        if course_token:
            slug, run = course_token.split("_")
            course = Course.objects.get(slug=slug, run=run)
            courses.append(course)
            target_courses_msg = course_token
        else:
            courses = Course.objects.filter(enable_badges=True).all()
            target_courses_msg = ",".join([course.token for course in courses])

        if username:
            users = [User.objects.get(username=username)]
            target_user_msg = f"username: {username}"
        else:
            target_user_msg = "(all users)"
            users = User.objects.all()

        logger.info(f"Creating badge assertion for username {target_courses_msg} in courses {target_user_msg}")

        for course in courses:
            logger.info(f" ")
            logger.info(f"Creating badges for course: {course.display_name} ")
            badge_class = BadgeClass.objects.get(course=course,
                                                 type=BadgeClassType.COURSE_PASSED.name)
            badge_service = get_badge_service()
            for user in users:
                logger.info(f"User: {user.username}")
                try:
                    ba = badge_service.issue_badge_assertion(badge_class=badge_class,
                                                             recipient=user,
                                                             do_async=False)
                    logger.info(f"Badge assertion created: {ba}")
                except Exception as e:
                    logger.exception(f"Could not create badge assertion "
                                     f"for user {user.username} "
                                     f"badge_class: {badge_class} : {e}")
                    continue
