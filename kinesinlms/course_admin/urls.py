from django.urls import path, include

from . import views

app_name = "course_admin"
urlpatterns = [
    path("", views.index, name="index"),
    path(
        "assessments/",
        views.assessments_index,
        name="assessments",
    ),
    path(
        "assessments/reset",
        views.DeleteSubmittedAnswersView.as_view(),
        name="delete_submitted_answers",
    ),
    path(
        "assessments/rescore",
        views.RescoreSubmittedAnswersView.as_view(),
        name="rescore_submitted_answers",
    ),
    path(
        "resources/",
        views.resources_index,
        name="resources",
    ),
    path(
        "resources/<int:pk>",
        views.resource_detail,
        name="resource_detail",
    ),
    path(
        "enrollment/",
        include("kinesinlms.course_enrollment.urls", namespace="course_enrollment"),
    ),
    path(
        "analytics/",
        include("kinesinlms.course_analytics.urls", namespace="course_analytics"),
    ),
    path(
        "cohorts/",
        include("kinesinlms.cohorts.urls", namespace="cohorts"),
    ),
]
