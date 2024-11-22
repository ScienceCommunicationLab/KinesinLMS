"""
URLs for creating and editing blocks within a course unit.

NOTE: Although it makes the URLs kind of ugly, it's important we pass in
the IDs for the module, section, unit, and course_unit, because we sometimes need to
know about where the block is situated in the course when editing it.

"""

from django.urls import path

from . import views

app_name = "blocks"

urlpatterns = [
    
    # Regular urls
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # ( none yet )

    # HTMx urls
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path(
        "<int:pk>/upload_course_resource/",
        views.block_resource_upload_hx,
        name="block_resource_upload_hx",
    ),
    path(
        "module/<int:module_node_id>"
        "/section/<int:section_node_id>"
        "/unit/<int:unit_node_id>"
        "/course_unit/<int:course_unit_id>"
        "/block/<int:pk>/",
        views.view_course_unit_block_hx,
        name="view_course_unit_block_hx",
    ),
    path(
        "module/<int:module_node_id>"
        "/section/<int:section_node_id>"
        "/unit/<int:unit_node_id>"
        "/course_unit/<int:course_unit_id>"
        "/block/<int:pk>"
        "/edit/",
        views.edit_block_panel_set_hx,
        name="edit_block_panel_set_hx",
    ),
    path(
        "module/<int:module_node_id>"
        "/section/<int:section_node_id>"
        "/unit/<int:unit_node_id>"
        "/course_unit/<int:course_unit_id>"
        "/block/<int:pk>"
        "/delete/",
        views.delete_course_unit_block_hx,
        name="delete_course_unit_block_hx",
    ),
    # When working with block resources, it's not
    # necessary for the routes to have information about
    # the module, section, unit, or course_unit.
    path(
        "<int:pk>/block_resource",
        views.block_resources_list_hx,
        name="block_resources_list_hx",
    ),
    path(
        "<int:pk>/block_resource/add",
        views.add_block_resource_hx,
        name="add_block_resource_hx",
    ),
    path(
        "<int:pk>/block_resource/select_from_library",
        views.select_block_resource_from_library_hx,
        name="select_block_resource_from_library_hx",
    ),
    path(
        "<int:block_id>/block_resource/<int:pk>/",
        views.delete_block_resource_hx,
        name="delete_block_resource_hx",
    ),
]
