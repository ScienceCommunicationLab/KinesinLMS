from django.urls import path

from . import views
from . import views_course
from . import views_provider

app_name = "management"
urlpatterns = [
    
    # Manage system...
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path("", views.index, name="index"),
    path(
        "site_profile/",
        views.SiteProfileUpdateView.as_view(),
        name="site_profile",
    ),
    path("site_features/", views.SiteFeaturesView.as_view(), name="site_features"),

    # Manage various service integrations...
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # FORUM PROVIDER
    path("forum_provider/", views_provider.forum_provider, name="forum_provider"),
    # EXTERNAL TOOL PROVIDER
    path(
        "external_tool/",
        views_provider.ExternalToolProviderListView.as_view(),
        name="external_tool_provider_list",
    ),
    path(
        "external_tool/create/",
        views_provider.ExternalToolProviderCreateView.as_view(),
        name="external_tool_provider_create",
    ),
    path(
        "external_tool/<int:pk>/",
        views_provider.ExternalToolProviderDetailView.as_view(),
        name="external_tool_provider_detail",
    ),
    path(
        "external_tool/<int:pk>/update/",
        views_provider.ExternalToolProviderUpdateView.as_view(),
        name="external_tool_provider_update",
    ),
    path(
        "external_tool/<int:pk>/delete/",
        views_provider.ExternalToolProviderDeleteView.as_view(),
        name="external_tool_provider_delete",
    ),
    # SURVEY PROVIDER
    path(
        "survey_provider/",
        views_provider.SurveyProviderListView.as_view(),
        name="survey_provider_list",
    ),
    path(
        "survey_provider/create/",
        views_provider.SurveyProviderCreateView.as_view(),
        name="survey_provider_create",
    ),
    path(
        "survey_provider/<int:pk>/",
        views_provider.SurveyProviderDetailView.as_view(),
        name="survey_provider_detail",
    ),
    path(
        "survey_provider/<int:pk>/update/",
        views_provider.SurveyProviderUpdateView.as_view(),
        name="survey_provider_update",
    ),
    path(
        "survey_provider/<int:pk>/delete/",
        views_provider.SurveyProviderDeleteView.as_view(),
        name="survey_provider_delete",
    ),
    # EMAIL AUTOMATION PROVIDER
    path(
        "email_automation_provider/",
        views_provider.email_automation_provider,
        name="email_automation_provider",
    ),
    # BADGE PROVIDER
    path("badge_provider/", views_provider.badge_provider, name="badge_provider"),
    # Manage students...
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path("student_management/", views.students_management, name="students_manage"),
    path(
        "student_management/students",
        views.StudentsListView.as_view(),
        name="students_list",
    ),
    path(
        "student_management/students/<int:user_id>/sync_student_to_discourse",
        views.sync_student_to_discourse,
        name="sync_student_to_discourse",
    ),
    path(
        "student_management/students/<int:user_id>/certificate/<int:certificate_id>",
        views.student_certificate,
        name="student_certificate",
    ),
    path(
        "student_management/students/manual_enrollment",
        views.ManualEnrollmentFormView.as_view(),
        name="students_manual_enrollment",
    ),
    path(
        "student_management/students/manual_unenrollment",
        views.ManualUnenrollmentFormView.as_view(),
        name="students_manual_unenrollment",
    ),
    path(
        "student_management/students/manual_enrollment_success/<int:pk>/",
        views.students_manual_enrollment_success,
        name="students_manual_enrollment_success",
    ),
    path(
        "student_management/students/manual_unenrollment_success/<int:pk>/",
        views.students_manual_unenrollment_success,
        name="students_manual_unenrollment_success",
    ),
    # Manage courses and students in courses...
    path("courses/", views_course.CourseListView.as_view(), name="courses_list"),
    path(
        "courses/<slug:course_slug>/<slug:course_run>/students/",
        views_course.students_in_course_list,
        name="students_in_course_list",
    ),
    path(
        "courses/<slug:course_slug>/<slug:course_run>/copy",
        views_course.duplicate_course,
        name="duplicate_course",
    ),
    path(
        "courses/<slug:course_slug>/<slug:course_run>/delete",
        views_course.delete_course,
        name="course_delete",
    ),
    path(
        "courses/<slug:course_slug>/<slug:course_run>/update",
        views_course.CourseUpdateView.as_view(),
        name="course_update",
    ),
    path(
        "courses/<slug:course_slug>/<slug:course_run>/badge_classes/",
        views_course.CourseBadgeClassListView.as_view(),
        name="course_badge_classes",
    ),
    path(
        "courses/<slug:course_slug>/<slug:course_run>/badge_assertions/",
        views_course.CourseBadgeAssertionListView.as_view(),
        name="course_badge_assertions",
    ),
    # UI controls
    path("admin_controls/", views.toggle_admin_controls, name="toggle_admin_controls"),
    # HTMx URLs for partial edits...
    # ..........................................................
    path(
        "hx/cohorts_select/<int:course_id>/",
        views.cohorts_select_hx,
        name="cohorts_select_hx",
    ),
    path(
        "email_automation_provider/hx/test_api",
        views_provider.email_automation_provider_test_api_hx,
        name="email_automation_provider_test_api_hx",
    ),
]
