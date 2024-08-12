from django.urls import path

from . import views

app_name = "cohorts"
urlpatterns = [

    path('',
         views.index,
         name="index"),

    path('create',
         views.CreateCohortView.as_view(),
         name="cohort_create"),

    path("<int:cohort_id>/download",
         views.download_cohort_info,
         name="cohort_download"),

    path("<int:cohort_id>/edit",
         views.EditCohortView.as_view(),
         name="cohort_edit"),

    path("<int:cohort_id>/delete",
         views.cohort_delete,
         name="cohort_delete"),

    path("<int:cohort_id>/students/<int:student_id>/",
         views.cohort_student,
         name="cohort_student"),

    # HTMx URLS for partial edits...
    # ..........................................................

    path("<int:cohort_id>/",
         views.cohort_hx,
         name="cohort_hx"),

    path("<int:cohort_id>/students/",
         views.cohort_students_hx,
         name="cohort_students_hx"),

    # Add a student to this cohort
    # TODO: THis should be a POST to the above URL...
    path("<int:cohort_id>/students/add/<int:student_id>/",
         views.cohort_move_student_hx,
         name="cohort_move_student_hx"),
]
