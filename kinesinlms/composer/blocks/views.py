import json
import logging

from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render

from kinesinlms.composer.blocks.builder import PanelSetManager
from kinesinlms.composer.blocks.forms.block_resource import ResourceForm
from kinesinlms.composer.blocks.panels.panels import PanelSet, PanelType
from kinesinlms.core.decorators import composer_author_required
from kinesinlms.course.models import Course, CourseNode, CourseUnit
from kinesinlms.learning_library.constants import (
    BlockViewContext,
    BlockViewMode,
    ResourceType,
)
from kinesinlms.learning_library.models import Block, BlockResource, UnitBlock

logger = logging.getLogger(__name__)

User = get_user_model()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# VIEW CLASSES
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ( none )

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# VIEW METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# HTMx METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@composer_author_required
def block_resource_upload_hx(request, course_id: int, pk: int):
    """
    Upload a resource to be associated with a block. This method is primarily
    meant for the drag-and-drop feature attached to the HTML Content portion
    of a panel form. Since the request will be a simple POST request, we don't
    need to return a template,just an acknowledgement that the resource was
    saved and some information about the new model.
    """
    course = get_object_or_404(Course, id=course_id)
    block = get_object_or_404(Block, id=pk)
    logger.debug(f"Adding block resource to course {course} block {block}")

    if request.method == "POST":
        file_obj = request.FILES["resource_file"]
        file_name_suffix = file_obj.name.split(".")[-1]
        if file_name_suffix not in [
            "jpg",
            "png",
            "gif",
            "jpeg",
        ]:
            return HttpResponseBadRequest(
                "Wrong file format. Only jpg, jpeg, png, and gif are allowed."
            )

        form = ResourceForm(request.POST, request.FILES, block=block)
        if form.is_valid(block=block):
            resource = form.save()
            logger.debug(f"Created Resource {resource}")
            block_resource = BlockResource.objects.create(
                block=block, resource=resource
            )
            logger.debug(f"Created BlockResource {block_resource}")
            response = JsonResponse(
                {
                    "message": "Resource uploaded successfully.",
                    "resource_url": resource.resource_file.url,
                },
                status=201,
            )
            return response
        else:
            return HttpResponseBadRequest("Invalid form data.")
    else:
        return HttpResponseBadRequest("POST method required.")


@composer_author_required
def view_course_unit_block_hx(
    request,
    course_id: int,
    course_unit_id: int,
    module_node_id: int,
    section_node_id: int,
    unit_node_id: int,
    pk: int,
):
    """
    Show the block in the 'read only' authoring mode.
    """
    course = get_object_or_404(Course, id=course_id)
    course_unit = get_object_or_404(CourseUnit, id=course_unit_id, course=course)
    module_node = get_object_or_404(CourseNode, id=module_node_id)
    section_node = get_object_or_404(CourseNode, id=section_node_id)
    unit_node = get_object_or_404(CourseNode, id=unit_node_id)

    block = get_object_or_404(Block, id=pk)

    unit_block: UnitBlock = UnitBlock.objects.get(
        course_unit=course_unit, block=block.id
    )

    context = {
        "block_view_context": BlockViewContext.COMPOSER.name,
        "block": block,
        "unit_block": unit_block,
        "course": course,
        "module_node": module_node,
        "module_slug": module_node.slug,
        "section_node": section_node,
        "section_slug": section_node.slug,
        "unit_node": unit_node,
        "unit_slug": unit_node.slug,
        "course_unit": course_unit,
        "block_view_mode": BlockViewMode.READ_ONLY.name,
    }

    template = "composer/course/course_unit/course_unit_block.html"

    htmx_event = {
        "editBlockPanelDeactivated": {
            "unit_block_id": unit_block.id,
            "block_id": block.id,
        }
    }

    response = render(request, template, context)
    response.headers["HX-Trigger"] = json.dumps(htmx_event)

    return response


@composer_author_required
def delete_course_unit_block_hx(
    request,
    course_id: int,
    course_unit_id: int,
    module_node_id: int,
    section_node_id: int,
    unit_node_id: int,
    pk: int,
):
    if request.method != "DELETE":
        return HttpResponseBadRequest("DELETE method required.")

    course = get_object_or_404(Course, id=course_id)
    course_unit = get_object_or_404(CourseUnit, id=course_unit_id, course=course)
    module_node = get_object_or_404(CourseNode, id=module_node_id)
    section_node = get_object_or_404(CourseNode, id=section_node_id)
    unit_node = get_object_or_404(CourseNode, id=unit_node_id)

    block = get_object_or_404(Block, id=pk)

    course_unit.delete_block(block=block)

    return HttpResponse("")


@composer_author_required
def edit_block_panel_set_hx(
    request,
    course_id: int,
    course_unit_id: int,
    module_node_id: int,
    section_node_id: int,
    unit_node_id: int,
    pk: int,
):
    """
    Show a "panel set" for editing different parts of a block or a block-related
    model like Assessment.

    This view is called by HTMx when the user clicks on the "Edit" button
    on a read-only view of a block. It returns a panel set with information
    on how to edit each part of the block.

    This view also handles a POST request from any panel shown in the panel set,
    in which case it will handle the post and return an updated panel.

    """

    course = get_object_or_404(Course, id=course_id)
    course_unit = get_object_or_404(CourseUnit, id=course_unit_id, course=course)
    module_node = get_object_or_404(CourseNode, id=module_node_id)
    section_node = get_object_or_404(CourseNode, id=section_node_id)
    unit_node = get_object_or_404(CourseNode, id=unit_node_id)

    block = get_object_or_404(Block, id=pk)

    unit_block: UnitBlock = UnitBlock.objects.get(
        course_unit=course_unit, block=block.id
    )

    # try:
    #    form_class: type = get_composer_form_class_for_block(block)
    # except Exception:
    #    logger.exception(f"Could not get_composer_form_class_for_block() block {block}")
    #    return HttpResponseBadRequest(f"Could not get block form")

    current_panel_slug = request.GET.get("panel_slug", None)
    # Build the appropriate panel set for the given block.
    manager = PanelSetManager()
    manager.set_builder_for_block(block)
    panel_set: PanelSet = manager.build_panel_set()
    if current_panel_slug:
        current_panel = panel_set.set_current_panel(current_panel_slug)
    else:
        current_panel = panel_set.current_panel
        current_panel_slug = current_panel.slug

    context = {
        "course_id": course_id,
        "block_view_context": BlockViewContext.COMPOSER.name,
        "block": block,
        "course": course,
        "module_node": module_node,
        "module_slug": module_node.slug,
        "section_node": section_node,
        "section_slug": section_node.slug,
        "unit_node": unit_node,
        "unit_slug": unit_node.slug,
        "course_unit": course_unit,
        "panel_set": panel_set,
        "current_panel_slug": current_panel_slug,
        "editing_block_id": block.id,
        "add_block_btn_disabled": True,
    }

    panel_form = None
    if current_panel.panel_type == PanelType.DJANGO_FORM.name:
        form_class = current_panel.form_class
        if request.POST:
            panel_form = form_class(
                request.POST,
                request.FILES,
                course=course,
                block=block,
                unit_block=unit_block,
                unit_node=unit_node,
                user=request.user,
            )
            if panel_form.is_valid():
                panel_form.save()
                context["saved_block_id"] = block.id

                # Run the form's post-save handler if there is one.
                if hasattr(panel_form, "post_save"):
                    panel_form.post_save()
        else:
            panel_form = form_class(
                course=course,
                block=block,
                unit_block=unit_block,
                unit_node=unit_node,
                user=request.user,
            )
    elif current_panel.panel_type == PanelType.HTMX.name:
        # TODO: any setup for panel's htmx stuff
        pass

    context["panel_form"] = panel_form
    context["has_file_upload"] = panel_form and panel_form.has_file_upload

    template = "composer/course/course_unit/course_unit_block.html"

    htmx_event = {
        "editBlockPanelActivated": {
            "unit_block_id": unit_block.id,
            "block_id": block.id,
            "current_panel_slug": current_panel_slug,
        }
    }
    response = render(request, template, context)
    response["HX-Trigger-After-Swap"] = json.dumps(htmx_event)
    return response


# BLOCK RESOURCES
# ..................................................................


@composer_author_required
def block_resources_list_hx(request, course_id: int, pk: int):
    block = get_object_or_404(Block, id=pk)
    course = get_object_or_404(Course, id=course_id)
    context = {
        "course": course,
        "course_id": course_id,
        "block": block,
        "block_resources": block.block_resources.all(),
    }
    return render(request, "composer/blocks/block_resources_table.html", context)


@composer_author_required
def select_block_resource_from_library_hx(request, course_id: int, pk: int):
    block = get_object_or_404(Block, id=pk)
    course = get_object_or_404(Course, id=course_id)
    if request.method == "POST":
        form = ResourceForm(request.POST, request.FILES, block=block)
        if form.is_valid():
            resource = form.save()
            logger.debug(f"Created Resource {resource}")
            response = HttpResponse(status=204)
            event_name = '{{"block{}ResourceAdded": "Block resource added."}}'.format(
                block.id
            )
            response.headers["HX-Trigger"] = event_name
            return response
    else:
        form = ResourceForm(block=block)

    context = {"course": course, "course_id": course_id, "form": form, "block": block}

    return render(
        request,
        "composer/blocks/dialogs/select_block_resource_from_library_modal_dialog.html",
        context,
    )


@composer_author_required
def add_block_resource_hx(request, course_id: int, pk: int):
    block = get_object_or_404(Block, id=pk)
    course = get_object_or_404(Course, id=course_id)
    if request.method == "POST":
        form = ResourceForm(request.POST, request.FILES, block=block)
        if form.is_valid():
            resource = form.save()
            logger.debug(f"Created Resource {resource}")
            response = HttpResponse(status=204)
            event_name = '{{"block{}ResourceAdded": "Block resource added."}}'.format(
                block.id
            )
            response.headers["HX-Trigger"] = event_name
            return response
    else:
        form = ResourceForm(block=block)

    context = {"course": course, "course_id": course_id, "form": form, "block": block}

    return render(
        request, "composer/blocks/dialogs/add_block_resource_modal_dialog.html", context
    )


@composer_author_required
def delete_block_resource_hx(request, course_id: int, block_id: int, pk: int):
    block_resource = get_object_or_404(BlockResource, id=pk, block__id=block_id)
    course = get_object_or_404(Course, id=course_id)
    resource = block_resource.resource
    block_resource.delete()
    logger.info(f"BlockResource {block_resource} deleted")
    block = get_object_or_404(Block, id=block_id)
    if resource.block_resources.count() == 0:
        resource.delete()
        logger.info(
            f"Deleted Resource {resource} as there are "
            f"no longer any blocks using it."
        )
    context = {
        "course": course,
        "course_id": course_id,
        "block": block,
        "block_resources": block.block_resources.all(),
    }
    return render(request, "composer/blocks/block_resources_table.html", context)
