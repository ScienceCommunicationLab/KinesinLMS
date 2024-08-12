from django.urls import path

from . import views

app_name = "catalog"
urlpatterns = [

    path("<slug:course_slug>/<slug:course_run>/enroll/",
         views.enroll,
         name="enroll"),

    path("<slug:course_slug>/<slug:course_run>/enroll/enrollment_survey",
         views.enrollment_survey,
         name="enrollment_survey"),

    path("<slug:course_slug>/<slug:course_run>/unenroll/",
         views.unenroll,
         name="unenroll"),

    path("<slug:course_slug>/<slug:course_run>/criteria/",
         views.criteria_page,
         name="criteria_page"),

    path("<slug:course_slug>/<slug:course_run>/",
         views.about_page,
         name="about_page"),

    path("<slug:course_slug>/",
         views.about_page,
         name="most_recent_run_about_page"),

    path("", views.index, name="index"),


]
