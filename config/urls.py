from django.conf import settings
from django.conf.urls.static import static

# DMcQ: Force use of allauth login for admin site
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from rest_framework import routers

from kinesinlms.analytics.views import EngagementDataViewSet
from kinesinlms.assessments.views import AssessmentViewSet, SubmittedAnswerViewSet
from kinesinlms.badges.views import BadgeAssertionViewSet
from kinesinlms.course.views import BookmarkViewSet, CourseNavViewSet, CourseViewSet
from kinesinlms.forum.views import TopicViewSet
from kinesinlms.learning_library.views import BlockViewSet, CourseUnitViewSet
from kinesinlms.pathways.views import PathwayViewSet
from kinesinlms.sits.views import (
    SimpleInteractiveToolSubmissionViewSet,
    SimpleInteractiveToolTemplateViewSet,
    SimpleInteractiveToolViewSet,
)
from kinesinlms.tracking.views import TrackingViewSet
from kinesinlms.users.api.views import UserViewSet

# Routers provide an easy way of automatically determining the URL conf.
from kinesinlms.users.views import UserProfilesViewSet

admin.site.login = login_required(admin.site.login)

# BASIC API URLS
# ================================================================================
router = routers.DefaultRouter()
router.register("users", UserViewSet)
router.register("answers", SubmittedAnswerViewSet, basename="answers")
router.register("assessments", AssessmentViewSet, basename="assessments")
router.register("badge_assertions", BadgeAssertionViewSet, basename="badge_assertions")
router.register("tracking", TrackingViewSet, basename="tracking")
router.register("bookmarks", BookmarkViewSet, basename="bookmarks")
router.register("blocks", BlockViewSet, basename="public_blocks")
router.register("course_units", CourseUnitViewSet, basename="public_units")
router.register("pathways", PathwayViewSet, basename="pathways")
router.register("forum", TopicViewSet, basename="forum")
router.register("courses", CourseViewSet, basename="courses")
router.register("course_nav", CourseNavViewSet, basename="course_nav")

# SIMPLE INTERACTIVE TOOLS
router.register(
    "simple_interactive_tools",
    SimpleInteractiveToolViewSet,
    basename="simple_interactive_tools",
)
# TODO: simple_interactive_tool_submissions should probably be nested under simple_interactive_tools...
router.register(
    "simple_interactive_tool_submissions",
    SimpleInteractiveToolSubmissionViewSet,
    basename="simple_interactive_tool_submissions",
)
# Only accessible to staff
router.register(
    "simple_interactive_tool_templates",
    SimpleInteractiveToolTemplateViewSet,
    basename="simple_interactive_tool_templates",
)

# ANALYTICS API URLS
# ================================================================================

# Engagement data
analytics_router = routers.DefaultRouter()
analytics_router.register(
    "engagement", EngagementDataViewSet, basename="analytics_course_engagement"
)

# User profile data
users_router = routers.DefaultRouter()
users_router.register(
    "user_profiles", UserProfilesViewSet, basename="users_user_profiles"
)


# noinspection PyUnresolvedReferences
urlpatterns = [
    path(
        "tinymce/",
        include("tinymce.urls"),
    ),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path(
        "users/",
        include("kinesinlms.users.urls", namespace="users"),
    ),
    # Main URLS
    path("accounts/", include("allauth.urls")),
    path("catalog/", include("kinesinlms.catalog.urls", namespace="catalog")),
    path("composer/", include("kinesinlms.composer.urls", namespace="composer")),
    path("courses/", include("kinesinlms.course.urls", namespace="course")),
    path("dashboard/", include("kinesinlms.dashboard.urls", namespace="dashboard")),
    path("forum/", include("kinesinlms.forum.urls", namespace="forum")),
    path(
        "external_tools/",
        include("kinesinlms.external_tools.urls", namespace="external_tools"),
    ),
    path(
        "jupyterlab/",
        include("kinesinlms.jupyterlab.urls", namespace="jupyterlab"),
    ),
    path(
        "learning_library/",
        include("kinesinlms.learning_library.urls", namespace="learning_library"),
    ),
    path("management/", include("kinesinlms.management.urls", namespace="management")),
    path("pathways/", include("kinesinlms.pathways.urls", namespace="pathways")),
    path("speakers/", include("kinesinlms.speakers.urls", namespace="speakers")),
    path("news/", include("kinesinlms.news.urls", namespace="news")),
    path("surveys/", include("kinesinlms.survey.urls", namespace="surveys")),
    path("resources/", include("kinesinlms.resources.urls", namespace="resources")),
    path("badges/", include("kinesinlms.badges.urls", namespace="badges")),
    path("help/", include("kinesinlms.help.urls", namespace="help")),
    # LTI and external tools
    path("lti/", include("kinesinlms.lti.urls", namespace="lti")),
    path("api/lti/", include("kinesinlms.lti.urls-api", namespace="lti-api")),
    # DRF stuff:
    path("api/analytics/", include(analytics_router.urls)),
    path("api/users/", include(users_router.urls)),
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),
    # Empty path goes to marketing
    path("", include("kinesinlms.marketing.urls", namespace="marketing")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
