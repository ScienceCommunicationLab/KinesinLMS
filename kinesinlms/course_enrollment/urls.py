from django.urls import path

from . import views

app_name = "course_enrollment"
urlpatterns = [
    path("", views.index, name="index"),
    path(
        "enrolled_students",
        views.EnrolledStudentsListView.as_view(),
        name="enrolled_students_list",
    ),
    path(
        "enrolled_students/<int:pk>/",
        views.EnrolledStudentDetailView.as_view(),
        name="enrolled_student_detail_view",
    ),
    path(
        "enrolled_students/<int:pk>/events",
        views.EnrolledStudentEventsListView.as_view(),
        name="enrolled_student_events_list",
    ),
    path(
        "manual_enrollment",
        views.manual_enrollment,
        name="manual_enrollment",
    ),
    path(
        "invited_users/",
        views.invited_users,
        name="invited_users",
    ),
    # HTMx views
    path(
        "invited_users/<int:invite_user_id>/delete",
        views.delete_invite_user_hx,
        name="delete_invite_user_hx",
    ),
]
