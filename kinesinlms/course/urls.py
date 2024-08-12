from django.urls import path, include

from . import views

app_name = "course"
urlpatterns = [

    path("<slug:course_slug>/<slug:course_run>/outline/",
         views.outline_course,
         name="outline_course"),

    path(
        "<slug:course_slug>/<slug:course_run>/content/<slug:module_slug>/<slug:section_slug>/<slug:unit_slug>/assessments/",
        include("kinesinlms.assessments.urls",
                namespace="assessments")),

    path("<slug:course_slug>/<slug:course_run>/course_admin/",
         include("kinesinlms.course_admin.urls",
                 namespace="course_admin")),

    path("<slug:course_slug>/<slug:course_run>/search/",
         views.course_search_page,
         name="course_search_page"),
    path("<slug:course_slug>/<slug:course_run>/extra/<slug:page_name>",
         views.course_extra_page,
         name="course_extra_page"),
    path("<slug:course_slug>/<slug:course_run>/certificate/",
         views.certificate_page,
         name="certificate_page"),
    path("<slug:course_slug>/<slug:course_run>/certificate/download",
         views.certificate_download,
         name="certificate_download"),

    # Progress section...
    path("<slug:course_slug>/<slug:course_run>/progress/",
         views.progress_redirect_view),
    path("<slug:course_slug>/<slug:course_run>/progress/overview",
         views.progress_overview_page,
         name="progress_overview_page"),
    path("<slug:course_slug>/<slug:course_run>/progress/detail/",
         views.progress_detail_page,
         name="progress_detail_page"),
    path("<slug:course_slug>/<slug:course_run>/progress/detail/<int:module_id>/",
         views.progress_detail_page,
         name="module_progress_detail_page"),

    path("<slug:course_slug>/<slug:course_run>/bookmarks/",
         views.bookmarks_page,
         name="bookmarks_page"),
    path("<slug:course_slug>/<slug:course_run>/forum_topics/",
         views.forum_topics_page,
         name="forum_topics_page"),
    path("<slug:course_slug>/<slug:course_run>/course_resource/<int:course_resource_id>",
         views.download_course_resource,
         name="download_course_resource"),
    path("<slug:course_slug>/<slug:course_run>/block_resource/<int:block_resource_id>",
         views.download_resource,
         name="download_resource"),
    path("<slug:course_slug>/<slug:course_run>/shortcut/units/<slug:unit_block_slug>",
         views.shortcut_to_unit,
         name="shortcut_to_unit"),
    path("<slug:course_slug>/<slug:course_run>/shortcut/assessments/<slug:unit_block_slug>",
         views.shortcut_to_assessment,
         name="shortcut_to_assessment"),
    path("<slug:course_slug>/<slug:course_run>/custom_app/<slug:custom_app_slug>/",
         views.custom_app_page,
         name="custom_app_page"),
    path(
        "<slug:course_slug>/<slug:course_run>/content/<slug:module_slug>/<slug:section_slug>/<slug:unit_slug>/<int:block_id>/",
        views.block_page,
        name="block_page"),
    path("<slug:course_slug>/<slug:course_run>/content/<slug:module_slug>/<slug:section_slug>/<slug:unit_slug>/",
         views.unit_page,
         name="unit_page"),
    path("<slug:course_slug>/<slug:course_run>/content/<slug:module_slug>/<slug:section_slug>/",
         views.redirect_to_unit_page,
         name="section_page"),
    path("<slug:course_slug>/<slug:course_run>/content/<slug:module_slug>/",
         views.redirect_to_unit_page,
         name="module_page"),
    path("<slug:course_slug>/<slug:course_run>/content/",
         views.redirect_to_unit_page,
         name="course_page"),

    path("<slug:course_slug>/<slug:course_run>/",
         views.course_home_page,
         name="course_home_page"),
    path("toggle_main_nav/",
         views.toggle_main_nav,
         name="toggle_main_nav"),

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # HTMx views
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    path("<slug:course_slug>/<slug:course_run>/summmary/<slug:module_slug>/<slug:section_slug>/<slug:unit_slug>/",
         views.unit_summary_hx,
         name="unit_page_summary_hx"),

    path(
        "<slug:course_slug>/<slug:course_run>/summmary/<slug:module_slug>/<slug:section_slug>/<slug:unit_slug>/toggle_bookmark",
        views.toggle_bookmark_hx,
        name="toggle_bookmark_hx"),

    path(
        "<slug:course_slug>/<slug:course_run>/forum_topics/<int:forum_topic_id>/posts/",
        views.forum_topic_posts_hx,
        name="forum_topic_posts_hx")

]
