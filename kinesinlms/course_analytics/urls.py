from django.urls import path

from . import views

app_name = "course_analytics"
urlpatterns = [

    path('',
         views.index,
         name="index"),

    path('student_progress/<int:cohort_id>/',
         views.student_progress,
         name="student_cohort_progress"),

    path('student_progress/report/<int:pk>/download',
         views.student_progress_report_download,
         name="student_progress_report_download"),

    path('student_progress/',
         views.student_progress,
         name="student_progress"),

    path('student_progress/report/<int:pk>/cancel',
         views.student_progress_report_cancel,
         name="student_progress_report_cancel"),



    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # HTMx views
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    path('student_progress/generate/hx/',
         views.student_progress_generate_hx,
         name="student_progress_generate_hx"),

    path('student_progress/<int:cohort_id>/generate/hx/',
         views.student_progress_generate_hx,
         name="student_cohort_progress_generate_hx"),

    path('student_progress/report/<int:pk>/hx/',
         views.student_progress_report_state_hx,
         name="student_progress_report_state_hx"),

]
