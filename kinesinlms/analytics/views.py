from django.db.models import Count
from rest_framework import viewsets, authentication, permissions
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from kinesinlms.course.constants import MilestoneType
from kinesinlms.course.models import Course, Milestone
from kinesinlms.course.serializers import MilestoneWithProgressesSerializer
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.models import TrackingEvent


class EngagementDataViewSet(viewsets.ViewSet):
    """
    Returns data about engagement, for use in building an
    'engagement grid' visualization.

    IMPORTANT: Make sure this is only available to 'admin' users,
    including the admin user used by kinesinlms-analytics to access API
    and get this ViewSet.
    """

    authentication_classes = [
        authentication.TokenAuthentication,
        authentication.SessionAuthentication,
    ]
    permission_classes = [permissions.IsAdminUser]

    def retrieve(self, request, pk):
        """
        Return engagement data for a course
        """
        queryset = Course.objects.all()
        course = get_object_or_404(queryset, id=pk)
        milestones = Milestone.objects.filter(course=course).prefetch_related()
        serializer = MilestoneWithProgressesSerializer(milestones, many=True)

        # Append 'default' milestones, which right now just means Forum posts.
        # TODO: Later make these proper models
        forum_milestone = get_forum_milestone(course)
        return_data = [forum_milestone] + serializer.data
        return Response(return_data)


# HELPER METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def get_forum_milestone(course: Course):
    forum_post_events = TrackingEvent.objects.filter(
        course_slug=course.slug,
        course_run=course.run,
        event_type=TrackingEventType.FORUM_POST.value,
    )

    passing_post_count = 10

    users_posts_counts = forum_post_events.values("user").annotate(
        event_count=Count("user")
    )

    users_posts = {}
    for user_posts in users_posts_counts.all():
        event_count = user_posts["event_count"]
        user_id = user_posts["user"]
        users_posts[user_id] = {
            "student": user_id,
            "count": event_count,
            "achieved": event_count >= passing_post_count,
        }

    # Make sure to report every student's counts, even those that have 0.
    progresses = []
    for user in course.enrollments.filter(active=True).all():
        count_obj = users_posts.get(
            user.id, {"student": user.id, "count": 0, "achieved": False}
        )
        progresses.append(count_obj)

    forum_milestone = {
        "course_token": course.token,
        "slug": "forum_posts",
        "name": "Forum Posts",
        "description": "Make at least 10 Forum Posts",
        "type": MilestoneType.FORUM_POSTS.name,
        "count_requirement": 10,
        "required_to_pass": False,
        "progresses": progresses,
    }
    return forum_milestone
