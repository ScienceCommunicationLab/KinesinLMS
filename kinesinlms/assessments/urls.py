from django.urls import path

from . import views

app_name = "assessments"
urlpatterns = [

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # HTMx views
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    path("<int:pk>/submitted_answer_hx/",
         views.assessment_submission_hx,
         name="assessment_submission_hx"),
]
