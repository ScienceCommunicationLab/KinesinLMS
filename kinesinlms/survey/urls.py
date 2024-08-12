from django.urls import path

from . import views

app_name = "surveys"

urlpatterns = [
    # This is the old callback I created using Qualtrics (semi-disfunctional) event subscriptions API
    # path("callback/", views.survey_event_callback, name="callback"),
    # This is the new callback meant to be used with Qualtrics callbacks created via the Qualtrics UI.
    path("student_survey_complete_callback/", views.student_survey_complete_callback, name="student_survey_complete_callback"),
]
