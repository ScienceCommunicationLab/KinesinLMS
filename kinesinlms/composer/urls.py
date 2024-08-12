from django.urls import include, path

from kinesinlms.composer.badges import views as badges_views
from kinesinlms.composer.email_automations import views as email_automations_views
from kinesinlms.composer.forum import views as forum_views
from kinesinlms.composer.milestones import views as milestones_views
from kinesinlms.composer.course_resources import views as course_resources_views
from kinesinlms.composer.course_surveys import views as course_surveys_views
from kinesinlms.sits import views as simple_interactive_tool_views
from . import views

app_name = "composer"

urlpatterns = [
    path("", views.home, name="home"),
    path("settings/", view=views.ComposerSettingsView.as_view(), name="settings"),
    # Course URLS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path("course/", views.course_list, name="course_list"),
    # UI to CRUD courses
    path("course/create", views.CourseCreateView.as_view(), name="course_create"),
    # Milestone editing URLS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path(
        "course/<int:course_id>/milestone/",
        milestones_views.CourseMilestonesListView.as_view(),
        name="course_milestones_list",
    ),
    path(
        "course/<int:course_id>/milestone/create/",
        milestones_views.CourseMilestoneCreateView.as_view(),
        name="course_milestone_create",
    ),
    path(
        "course/<int:course_id>/milestone/<int:pk>/",
        milestones_views.CourseMilestoneUpdateView.as_view(),
        name="course_milestone_update",
    ),
    # HTMx URLs for Milestones...
    # ..........................................................
    path(
        "course/<int:course_id>/milestone/<int:pk>/delete",
        milestones_views.course_milestone_delete_hx,
        name="course_milestone_delete_hx",
    ),
    # Resources editing URLS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path(
        "course/<int:course_id>/resource/",
        course_resources_views.ResourcesListView.as_view(),
        name="resources_list",
    ),
    path(
        "course/<int:course_id>/resource/course_resource/create/",
        course_resources_views.CourseResourceCreateView.as_view(),
        name="course_resource_create",
    ),
    path(
        "course/<int:course_id>/resource/course_resource/<int:pk>/",
        course_resources_views.CourseResourceUpdateView.as_view(),
        name="course_resource_update",
    ),
    path(
        "course/<int:course_id>/resource/educator_course_resource/create/",
        course_resources_views.EducatorCourseResourceCreateView.as_view(),
        name="educator_course_resource_create",
    ),
    path(
        "course/<int:course_id>/resource/educator_course_resource/<int:pk>/",
        course_resources_views.EducatorCourseResourceUpdateView.as_view(),
        name="educator_course_resource_update",
    ),
    # HTMx URLs for course resources...
    # ..........................................................
    path(
        "course/<int:course_id>/educator_course_resource/<int:pk>/delete",
        course_resources_views.course_resource_delete_hx,
        name="course_resource_delete_hx",
    ),
    path(
        "course/<int:course_id>/educator_course_resource/<int:pk>/delete",
        course_resources_views.educator_course_resource_delete_hx,
        name="educator_course_resource_delete_hx",
    ),
    # Survey editing URLS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path(
        "course/<int:course_id>/course_survey/",
        course_surveys_views.CourseSurveysListView.as_view(),
        name="course_surveys_list",
    ),
    path(
        "course/<int:course_id>/course_survey/create/",
        course_surveys_views.CourseSurveyCreateView.as_view(),
        name="course_survey_create",
    ),
    path(
        "course/<int:course_id>/course_survey/<int:pk>/",
        course_surveys_views.CourseSurveyUpdateView.as_view(),
        name="course_survey_update",
    ),
    # HTMx URLs for course surveys...
    # ..........................................................
    path(
        "course/<int:course_id>/course_survey/<int:pk>/delete",
        course_surveys_views.course_survey_delete_hx,
        name="course_survey_delete_hx",
    ),
    # Email automation URLs
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path(
        "course/<int:pk>/email_automations",
        email_automations_views.CourseEmailAutomationsSettingsUpdateView.as_view(),
        name="course_email_automations_settings_edit",
    ),
    # Badge editing URLs
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path(
        "course/<int:course_id>/badge_class/",
        badges_views.CourseBadgeClassListView.as_view(),
        name="course_badge_classes_list",
    ),
    path(
        "course/<int:course_id>/badge_class/create/",
        badges_views.CourseBadgeClassCreateView.as_view(),
        name="course_badge_class_create",
    ),
    path(
        "course/<int:course_id>/badge_class/<int:pk>/",
        badges_views.CourseBadgeClassUpdateView.as_view(),
        name="course_badge_class_update",
    ),
    # HTMx URLs for badges...
    # ..........................................................
    path(
        "course/<int:course_id>/badge_class/<int:pk>/delete",
        badges_views.course_badge_class_delete_hx,
        name="course_badge_class_delete_hx",
    ),
    # Forum editing URLS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path(
        "course/<int:course_id>/forum",
        views.course_forum_edit,
        name="course_forum_edit",
    ),
    # HTMx URLs for forums...
    # ..........................................................
    path(
        "course/<int:course_id>/forum/<slug:forum_item_slug>/create",
        forum_views.create_forum_item_hx,
        name="create_forum_item_hx",
    ),
    # Course editing URLs
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path(
        "course/<int:pk>/settings",
        views.CourseSettingsUpdateView.as_view(),
        name="course_edit_settings",
    ),
    path(
        "course/<int:course_id>/",
        views.course_edit,
        name="course_edit",
    ),
    path(
        "course/<int:pk>/delete",
        views.CourseDeleteView.as_view(),
        name="course_delete",
    ),
    path(
        "course/<int:course_id>/unit_node/<int:unit_node_id>",
        views.course_edit,
        name="course_edit_unit_node",
    ),
    path(
        "course/<int:course_id>/catalog/<int:pk>/",
        views.CourseCatalogDescriptionUpdateView.as_view(),
        name="course_catalog_description_edit",
    ),
    # HTMx URLs for partial edits...
    # ..........................................................
    path(
        "course/<int:pk>/course_nav",
        views.edit_course_nav_hx,
        name="edit_course_nav_hx",
    ),
    path(
        "course/<int:course_id>/module/<int:pk>/delete",
        views.delete_module_node_hx,
        name="delete_module_node_hx",
    ),
    path(
        "course/<int:course_id>"
        "/module/<int:module_node_id>"
        "/section/<int:pk>/delete",
        views.delete_section_node_hx,
        name="delete_section_node_hx",
    ),
    path(
        "course/<int:course_id>"
        "/module/<int:module_node_id>"
        "/section/<int:section_node_id>"
        "/unit_node/<int:pk>/delete",
        views.delete_unit_node_hx,
        name="delete_unit_node_hx",
    ),
    path(
        "course/<int:pk>/module/add",
        views.add_module_to_root_node_hx,
        name="add_module_node_to_root_node_hx",
    ),
    path(
        "course/<int:course_id>/module/<int:module_node_id>/section/add",
        views.add_section_node_to_module_hx,
        name="add_section_node_to_module_hx",
    ),
    path(
        "course/<int:course_id>"
        "/module/<int:module_node_id>"
        "/section/<int:section_node_id>"
        "/unit/add",
        views.add_unit_to_section_hx,
        name="add_unit_node_to_section_hx",
    ),
    path(
        "course/<int:course_id>"
        "/module/<int:module_node_id>"
        "/section/<int:section_node_id>"
        "/unit/<int:unit_node_id>"
        "/course_unit/<int:pk>/edit",
        views.edit_course_unit_hx,
        name="edit_course_unit_hx",
    ),
    path(
        "course/<int:course_id>"
        "/module/<int:module_node_id>"
        "/section/<int:section_node_id>"
        "/unit/<int:unit_node_id>"
        "/course_unit/<int:course_unit_id>/content_index/",
        views.edit_course_unit_info_hx,
        name="edit_course_unit_info_hx",
    ),
    path(
        "course/<int:course_id>"
        "/module/<int:module_node_id>"
        "/section/<int:section_node_id>"
        "/unit/<int:unit_node_id>"
        "/course_unit/<int:course_unit_id>"
        "/show_add_dialog",
        views.show_add_block_modal_dialog_hx,
        name="show_add_block_modal_dialog_hx",
    ),
    # Blocks
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Editing or displaying existing blocks....
    # Here we don't really need the path to a particular
    # course unit, since that shouldn't matter when editing
    # the block itself. However, we do include course_id, as that
    # might be relevant when editing or displaying the block.
    path(
        "course/<int:course_id>/block/",
        include("kinesinlms.composer.blocks.urls", namespace="blocks"),
    ),
    # Adding a new block to a course unit...
    path(
        "course/<int:course_id>"
        "/module/<int:module_node_id>"
        "/section/<int:section_node_id>"
        "/unit/<int:unit_node_id>"
        "/course_unit/<int:course_unit_id>"
        "/block/add/<slug:block_type>/",
        views.add_course_unit_block_hx,
        name="add_course_unit_block_type_hx",
    ),
    # Adding a new block (with subtype) to a course unit...
    path(
        "course/<int:course_id>"
        "/course_unit/<int:course_unit_id>"
        "/module/<int:module_node_id>"
        "/section/<int:section_node_id>"
        "/unit/<int:unit_node_id>"
        "/block/<slug:block_type>"
        "/subtype/<slug:block_subtype>/add",
        views.add_course_unit_block_hx,
        name="add_course_unit_block_type_subtype_hx",
    ),
    # Inserting an existing block into a course unit...
    path(
        "course/<int:course_id>"
        "/module/<int:module_node_id>"
        "/section/<int:section_node_id>"
        "/unit/<int:unit_node_id>"
        "/course_unit/<int:course_unit_id>"
        "/block/insert",
        views.insert_existing_course_unit_block_hx,
        name="insert_existing_course_unit_block_hx",
    ),
    # Course import / export
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path(
        "course/export/<slug:course_slug>/<slug:course_run>/",
        views.course_download_export,
        name="course_download_export",
    ),
    path("course/import/", views.course_import_view, name="course_import_view"),
    path("course/export/", views.course_export_view, name="course_export_view"),
    # SIT URLs
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path(
        "simple_interactive_tool_templates/<int:template_id>/description",
        simple_interactive_tool_views.SimpleInteractiveToolTemplateUpdateView.as_view(),
        name="simple_interactive_tool_template_description",
    ),
    path(
        "simple_interactive_tool_templates/create",
        simple_interactive_tool_views.SimpleInteractiveToolTemplateCreateView.as_view(),
        name="simple_interactive_tool_template_create",
    ),
    path(
        "simple_interactive_tool_templates/<int:template_id>/delete",
        simple_interactive_tool_views.SimpleInteractiveToolTemplateDeleteView.as_view(),
        name="simple_interactive_tool_template_delete",
    ),
    path(
        "simple_interactive_tool_templates/<int:template_id>/",
        simple_interactive_tool_views.SimpleInteractiveToolTemplateDetailView.as_view(),
        name="simple_interactive_tool_template_design",
    ),
    path(
        "simple_interactive_tool_templates/",
        simple_interactive_tool_views.SimpleInteractiveToolTemplateListView.as_view(),
        name="simple_interactive_tool_templates_list",
    ),


    # HTMx URLs
    # ..........................................................
    path(
        "toggle_wysiwyg/",
        views.toggle_wysiwyg_hx,
        name="toggle_wysiwyg_hx",
    ),

]
