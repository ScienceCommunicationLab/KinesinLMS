import json
import logging
from io import BytesIO
from typing import Any, Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
    HttpResponseServerError,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from kinesinlms.badges.models import BadgeClass
from kinesinlms.catalog.models import CourseCatalogDescription
from kinesinlms.composer.factory import (
    CourseBuilderDirector,
    SimpleCourseBuilder,
    create_module_node,
    create_section_node,
    create_unit_node,
    get_course_exporter,
)
from kinesinlms.composer.forms.catalog import CourseCatalogDescriptionForm
from kinesinlms.composer.forms.course import (
    CourseForm,
    DeleteCourseForm,
    EditCourseHeaderForm,
    ImportCourseFromArchiveForm,
)
from kinesinlms.composer.forms.settings import ComposerSettingsForm
from kinesinlms.composer.import_export.constants import (
    CourseExportFormat,
)
from kinesinlms.composer.import_export.exporter import BaseExporter
from kinesinlms.composer.import_export.kinesinlms.constants import (
    VALID_COURSE_EXPORT_FORMAT_IDS,
)
from kinesinlms.composer.import_export.kinesinlms.importer import KinesinLMSCourseImporter
from kinesinlms.composer.models import ComposerSettings, CourseImportTaskResult, CourseImportTaskStatus
from kinesinlms.composer.tasks import generate_course_import_task
from kinesinlms.composer.view_helpers import get_course_edit_tabs
from kinesinlms.core.decorators import composer_author_required
from kinesinlms.course.constants import CourseUnitType, NodeType
from kinesinlms.course.delete_utils import delete_course, get_exclusive_resources
from kinesinlms.course.models import Course, CourseNode, CourseUnit
from kinesinlms.course.views import get_course_nav
from kinesinlms.forum.models import (
    CourseForumGroup,
    ForumCategory,
    ForumSubcategory,
    ForumSubcategoryType,
)
from kinesinlms.forum.utils import get_forum_provider, get_forum_service
from kinesinlms.learning_library.builders import BlockBuilderDirector
from kinesinlms.learning_library.constants import (
    AssessmentType,
    BlockType,
    BlockViewContext,
    BlockViewMode,
)
from kinesinlms.learning_library.models import Block, UnitBlock
from kinesinlms.management.utils import delete_course_nav_cache
from kinesinlms.sits.constants import SimpleInteractiveToolType
from kinesinlms.users.mixins import (
    StaffOrSuperuserRequiredMixin,
    SuperuserRequiredMixin,
)

logger = logging.getLogger(__name__)

User = get_user_model()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# View Classes
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class CourseCreateView(SuperuserRequiredMixin, CreateView):
    model = Course
    template_name = "composer/course/course_create.html"
    form_class = CourseForm

    def form_valid(self, form):
        """
        We use a director and builder here to create the course
        rather than a relying on the model form. Maybe overkill
        because at the moment we only have one kind of basic course
        structure. But having the director and builder in place will
        make it easier to add more complex course structures later.
        """
        director = CourseBuilderDirector(builder=SimpleCourseBuilder())
        course = director.create_course(**form.cleaned_data)
        logger.info(f"Created new course : {course}")
        self.object = course
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        success_msg = _(
            "Course {} created. You may now edit the " "catalog description and add content " "to the course.".format(
                self.object.token
            )
        )
        messages.add_message(self.request, messages.INFO, success_msg)
        edit_url = reverse("composer:course_edit_settings", kwargs={"pk": self.object.id})
        return edit_url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Course"
        context["active"] = "course_create"
        context["description"] = "Create a new course"

        return context


class CourseSettingsUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Course
    template_name = "composer/course/course_update_settings.html"
    form_class = CourseForm

    def get_success_url(self):
        messages.add_message(self.request, messages.INFO, f"Course {self.object.token} updated.")
        edit_course_url = reverse("composer:course_edit_settings", kwargs={"pk": self.object.id})
        return edit_course_url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object and self.object.display_name:
            course_name = self.object.display_name
        else:
            course_name = "( no name )"

        section_tabs = get_course_edit_tabs(current_course=self.object, active_section="course_settings")
        extra_context = {
            "section": "edit_course",
            "title": f"Edit Course : {course_name}",
            "breadcrumbs": [],
            "section_tabs": section_tabs,
        }
        context.update(extra_context)

        return context


class CourseCatalogDescriptionUpdateView(SuperuserRequiredMixin, UpdateView):
    model = CourseCatalogDescription
    template_name = "composer/catalog/course_catalog_description_form.html"
    form_class = CourseCatalogDescriptionForm

    def get_success_url(self) -> str:
        messages.add_message(
            self.request,
            messages.INFO,
            f"Catalog Description {self.object.course.token} updated.",
        )
        course = self.object.course
        return reverse(
            "composer:course_catalog_description_edit",
            kwargs={"course_id": course.id, "pk": self.object.id},
        )

    def get_form_kwargs(self):
        """
        Send relevant user settings props to the form.
        """
        kwargs = super().get_form_kwargs()
        user_settings = ComposerSettings.objects.get_or_create(user=self.request.user)[0]
        kwargs["html_edit_mode"] = user_settings.html_edit_mode
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        course_id = self.kwargs["course_id"]
        course = get_object_or_404(Course, id=course_id)

        course_name = course.display_name
        if not course_name:
            course_name = "( no name )"

        section_tabs = get_course_edit_tabs(current_course=self.object.course, active_section="catalog")

        extra_context = {
            "section": "edit_course",
            "title": f"Edit Course : {course_name}",
            "breadcrumbs": [],
            "section_tabs": section_tabs,
            "current_course": course,
        }
        context.update(extra_context)

        return context


class CourseBadgeClassListView(SuperuserRequiredMixin, ListView):
    model = BadgeClass
    template_name = "composer/badges/course_badge_classes_list.html"
    context_object_name = "badge_classes"

    def get_queryset(self):
        course_id = self.kwargs["course_id"]
        course = get_object_or_404(Course, id=course_id)
        return course.badge_classes.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        course_id = self.kwargs["course_id"]
        course = get_object_or_404(Course, id=course_id)

        course_name = course.display_name
        if not course_name:
            course_name = "( no name )"

        section_tabs = get_course_edit_tabs(current_course=course, active_section="course_settings")
        extra_context = {
            "section": "edit_course",
            "title": f"Edit Course : {course_name}",
            "breadcrumbs": [],
            "section_tabs": section_tabs,
        }
        context.update(extra_context)

        return context


class ComposerSettingsView(StaffOrSuperuserRequiredMixin, UpdateView):
    """
    Provides an editable page for composer settings.

    We should always have a ComposerSettings object, so no need for a CreateView.

    """

    template_name = "composer/composer_settings_detail.html"

    form_class = ComposerSettingsForm
    model = ComposerSettings

    def get_object(self, queryset=None):
        composer_settings, created = ComposerSettings.objects.get_or_create(user=self.request.user)
        return composer_settings

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.add_message(self.request, messages.INFO, "Composer settings saved.")
        return response

    def get_success_url(self) -> str:
        return reverse("composer:settings")


class CourseDeleteView(SuperuserRequiredMixin, DeleteView):
    model = Course
    template_name = "composer/course/course_confirm_delete.html"
    context_object_name = "course"
    form_class = DeleteCourseForm

    def get_context_data(self, **kwargs: reverse_lazy) -> dict[str, Any]:
        course = self.get_object()
        context = super().get_context_data(**kwargs)
        exclusive_resources = get_exclusive_resources(course=self.object)
        breadcrumbs = [
            {
                "label": f"Edit Course : {course.display_name}",
                "url": reverse("composer:course_edit_settings", args=[course.id]),
            }
        ]
        context["exclusive_resources"] = exclusive_resources
        context["title"] = "Delete Course Confirmation"
        context["breadcrumbs"] = breadcrumbs
        return context

    def get_success_url(self):
        url = reverse("composer:course_list")
        return url

    # Django has this weird setup where form_valid is called on POST
    # but delete is called on DELETE. So we need to have both
    # point to the same method.

    def form_valid(self, form):
        return self._delete_course()

    def delete(self, request, *args, **kwargs):
        return self._delete_course()

    def _delete_course(self):
        self.object = self.get_object()
        course = self.object
        success_url = self.get_success_url()

        delete_exclusive_block_resources = self.request.POST.get("delete_block_resources") == "on"

        try:
            with transaction.atomic():
                warnings = delete_course(
                    course,
                    delete_all_progress=False,
                    delete_exclusive_block_resources=delete_exclusive_block_resources,
                )
                messages.success(self.request, "Course deleted successfully.")
                if warnings:
                    for warning in warnings:
                        messages.warning(self.request, warning)
        except Exception as e:
            logger.exception(f"Error deleting course {course}: {e}")
            messages.error(self.request, f"Error deleting course {course}")

        return HttpResponseRedirect(success_url)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# View Methods
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@composer_author_required
def home(request):
    course_descriptions = CourseCatalogDescription.objects.filter()
    context = {
        "active": "home",
        "title": "Home",
        "course_descriptions": course_descriptions,
    }
    return render(request, "composer/home.html", context)


@composer_author_required
def course_list(request):
    """
    List all courses availble for editing.
    """
    course_descriptions = CourseCatalogDescription.objects.filter()

    context = {
        "title": "Course List",
        "active": "course_list",
        "course_descriptions": course_descriptions,
    }
    return render(request, "composer/course/course_list.html", context)


@composer_author_required
def course_edit(request, course_id: int, unit_node_id: int = None):
    course = get_object_or_404(Course, id=course_id)

    # By default we're going to bust the nav cache.
    # TODO:
    #   more granular approach that only busts
    #   cache when necessary when editing in composer.
    delete_course_nav_cache(course_slug=course.slug, course_run=course.run)

    display_name = course.display_name or "( no display name defined )"

    course_nav = get_course_nav(course)

    section_tabs = get_course_edit_tabs(current_course=course, active_section="content")

    context = {
        "title": f"Edit Course : {display_name}",
        "section": "edit_course",
        "course": course,
        "course_nav": course_nav,
        "admin_base_url": settings.ADMIN_URL,
        "section_tabs": section_tabs,
    }

    unit_node = None
    if unit_node_id:
        unit_node = get_object_or_404(CourseNode, id=unit_node_id, type=NodeType.UNIT.name)
    else:
        # Find first unit node...
        try:
            module_node = course.course_root_node.get_children()[0]
            section_node = module_node.get_children()[0]
            unit_node = section_node.get_children()[0]
        except Exception:
            logger.error("Could not find first unit node")

    if unit_node:
        course_unit = unit_node.unit
        section_node = unit_node.parent
        module_node = section_node.parent
        content_index_label = (
            f"{module_node.content_index}." f"{section_node.content_index}." f"{unit_node.content_index}"
        )
        extra_context = {
            "block_view_context": BlockViewContext.COMPOSER.name,
            "block_view_mode": BlockViewMode.READ_ONLY.name,
            "module_node": module_node,
            "module_slug": module_node.slug,
            "section_node": section_node,
            "section_slug": section_node.slug,
            "unit_node": unit_node,
            "unit_slug": unit_node.slug,
            "course_unit": course_unit,
            "content_index_label": content_index_label,
            "show_blocks_collapsed": True,
        }
        context = context | extra_context

    return render(request, "composer/course/course_edit.html", context)


@composer_author_required
def course_forum_edit(request, course_id: int, unit_node_id: int = None):
    course = get_object_or_404(Course, id=course_id)

    section_tabs = get_course_edit_tabs(
        current_course=course,
        active_section="course_forum",
    )

    forum_provider = get_forum_provider()
    forum_service = get_forum_service()

    if forum_provider and forum_provider.active:
        # TODO: Set this if any one configuration needs to be set.
        show_configure_all_btn = True
    else:
        show_configure_all_btn = False

    try:
        course_forum_group = CourseForumGroup.objects.get(course=course)
    except CourseForumGroup.DoesNotExist:
        course_forum_group = None

    try:
        course_forum_category = ForumCategory.objects.get(course=course)
    except ForumCategory.DoesNotExist:
        course_forum_category = None

    default_cohort = course.get_default_cohort()
    if course_forum_category:
        try:
            default_cohort_forum_subcategory = ForumSubcategory.objects.get(
                forum_category=course_forum_category,
                type=ForumSubcategoryType.COHORT.name,
                cohort_forum_group=default_cohort.cohort_forum_group,
            )
        except ForumSubcategory.DoesNotExist:
            default_cohort_forum_subcategory = None
    else:
        default_cohort_forum_subcategory = None

    default_cohort = course.get_default_cohort()
    default_cohort_forum_group = default_cohort.cohort_forum_group

    context = {
        "title": "Course Forum",
        "section": "edit_course",
        "forum_provider": forum_provider,
        "forum_service": forum_service,
        "course": course,
        "admin_base_url": settings.ADMIN_URL,
        "section_tabs": section_tabs,
        "show_configure_all_btn": show_configure_all_btn,
        "default_cohort": default_cohort,
        "course_forum_group": course_forum_group,
        "default_cohort_forum_group": default_cohort_forum_group,
        "course_forum_category": course_forum_category,
        "default_cohort_forum_subcategory": default_cohort_forum_subcategory,
    }

    return render(request, "composer/forum/course_forum.html", context)


@composer_author_required
def edit_course_unit_info_hx(
    request,
    course_id: int,
    module_node_id: int,
    section_node_id: int,
    unit_node_id: int,
    course_unit_id: int,
):
    """
    Allows editing of course unit title and content_index.
    """
    course = get_object_or_404(Course, id=course_id)
    course_unit = get_object_or_404(CourseUnit, id=course_unit_id, course=course)
    module_node = CourseNode.objects.get(id=module_node_id, type=NodeType.MODULE.name)
    section_node = CourseNode.objects.get(id=section_node_id, type=NodeType.SECTION.name)
    unit_node = CourseNode.objects.get(id=unit_node_id, type=NodeType.UNIT.name)

    content_index_label = f"{module_node.content_index}." f"{section_node.content_index}." f"{unit_node.content_index}"

    context = {
        "course": course,
        "course_unit": course_unit,
        "module_node": module_node,
        "module_slug": module_node.slug,
        "section_node": section_node,
        "section_slug": section_node.slug,
        "unit_node": unit_node,
        "unit_slug": unit_node.slug,
        "content_index_label": content_index_label,
    }
    template = "composer/course/course_unit/course_unit_header_edit.html"

    if request.method == "POST":
        edit_course_form = EditCourseHeaderForm(request.POST, instance=course_unit, user=request.user)
        if edit_course_form.is_valid():
            edit_course_form.save()
            delete_course_nav_cache(course.slug, course.run)
            template = "composer/course/course_unit/course_unit_header.html"
        else:
            # Leave form with errors
            pass
    else:
        if request.GET.get("cancel", False):
            edit_course_form = None
            template = "composer/course/course_unit/course_unit_header.html"
        else:
            edit_course_form = EditCourseHeaderForm(instance=course_unit, user=request.user)
            context["form"] = edit_course_form

    context["form"] = edit_course_form
    response = render(request, template, context)
    if edit_course_form:
        htmx_event = "editCourseUnitInfoActivated"
    else:
        htmx_event = "editCourseUnitInfoDeactivated"
    response["HX-Trigger"] = htmx_event
    return response


@composer_author_required
def course_export_view(request):
    """
    Displays a table of courses, each with a download button.
    """
    courses = Course.objects.all()
    context = {
        "section": "composer",
        "title": "Course Export",
        "description": "Export courses as a .zip archive.",
        "courses": courses,
    }
    return render(request, "composer/course/course_export.html", context)


@composer_author_required
def course_import_status_view(request, course_import_task_result_id):
    """
    Displays the status of a course import task.
    """
    task_result = get_object_or_404(CourseImportTaskResult, id=course_import_task_result_id)
    context = {
        "section": "composer",
        "title": "Course Import Status",
        "description": "Status of course import task.",
        "course_import_task_result": task_result,
        "breadcrumbs": [
            {"label": "Course Import", "url": reverse("composer:course_import_view")},
        ],
    }
    return render(request, "composer/course/course_import_status.html", context)


@composer_author_required
def course_import_cancel(request, course_import_task_result_id):
    """
    Cancel a course import task.
    """
    task_result = get_object_or_404(CourseImportTaskResult, id=course_import_task_result_id)
    task_result.cancel()
    messages.add_message(request, messages.INFO, "Course import task cancelled.")
    return HttpResponseRedirect(reverse("composer:course_import_view"))


@composer_author_required
def course_download_export(request, course_slug=None, course_run=None):
    """
    Export a course as a .zip file.
    Format can be specified in the query string.

    Supported formats:
    - KINESIN_LMS_ZIP
    - CC_FULL
    - CC_SLIM

    Args:
        request:
        course_slug:
        course_run:

    Returns
        HTTP response
    """

    export_format = request.GET.get("export_format", None)
    if not export_format:
        export_format = CourseExportFormat.KINESIN_LMS_ZIP.name

    if export_format not in [
        CourseExportFormat.KINESIN_LMS_ZIP.name,
        CourseExportFormat.OPEN_EDX.name,
        CourseExportFormat.COMMON_CARTRIDGE_FULL.name,
        CourseExportFormat.COMMON_CARTRIDGE_SLIM.name,
    ]:
        return HttpResponseBadRequest(f"Export format {export_format} not supported.")

    # Make sure to bust the nav cache before exporting
    delete_course_nav_cache(course_slug, course_run)

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    course_exporter: BaseExporter = get_course_exporter(export_format)
    export_filename = course_exporter.get_export_filename(course)

    try:
        zip_bytes: BytesIO = course_exporter.export_course(course=course, export_format=export_format)
        content_type = course_exporter.get_content_type()
        resp = HttpResponse(zip_bytes.getvalue(), content_type=content_type)
    except Exception as e:
        logger.exception(f"Could not export course: {e}")
        return HttpResponseServerError("Could not export course.")

    resp["Content-Disposition"] = "attachment; filename={}".format(export_filename)
    return resp


@composer_author_required
def course_import_view(request):
    context = {
        "section": "composer",
        "title": "Course Import",
        "description": "Import course from a .zip archive.",
    }
    # TODO: Consider whether staff should be able to import courses.
    if request.user.is_superuser is False:
        return HttpResponseForbidden()
    if request.method == "POST":
        form = ImportCourseFromArchiveForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                display_name = form.cleaned_data.get("display_name")
                course_slug = form.cleaned_data.get("course_slug")
                course_run = form.cleaned_data.get("course_run")
                create_forum_items = form.cleaned_data.get("create_forum_items", False)
                import_file = request.FILES["file"]

                if Course.objects.filter(slug=course_slug, run=course_run).exists():
                    messages.add_message(
                        request,
                        messages.ERROR,
                        "Course already exists with that slug and run. Please choose a different slug or run.",
                    )
                    context["form"] = form
                    return render(request, "composer/course/course_import.html", context)

                task_result, created = CourseImportTaskResult.objects.get_or_create(
                    course_slug=course_slug,
                    course_run=course_run,
                )

                redirect_url = reverse(
                    "composer:course_import_status_view",
                    kwargs={
                        "course_import_task_result_id": task_result.id,
                    },
                )

                if not created and task_result.generation_status in [
                    CourseImportTaskStatus.PENDING.name,
                    CourseImportTaskStatus.IN_PROGRESS.name,
                ]:
                    messages.add_message(
                        request,
                        messages.INFO,
                        _("Course import already underway. You will be notified when it is complete."),
                    )
                    return redirect(redirect_url)

                # Update task result with new data
                task_result.import_file = import_file
                task_result.display_name = display_name
                task_result.create_forum_items = create_forum_items
                task_result.generation_status = CourseImportTaskStatus.PENDING.name
                task_result.save()

                generate_course_import_task.apply_async(
                    kwargs={
                        "course_import_task_result_id": task_result.id,
                    },
                    countdown=3,
                )

                return redirect(redirect_url)

            except Exception as e:
                logger.error("Couldn't start course import process: {}".format(e))
                # temp
                raise e
                context["form"] = ImportCourseFromArchiveForm()
                msg = _("Couldn't parse course description in archive")
                messages.add_message(request, messages.ERROR, msg)
                context["form"] = form
        else:
            context["form"] = form
    else:
        context["form"] = ImportCourseFromArchiveForm()
    return render(request, "composer/course/course_import.html", context)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# HTMX METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@composer_author_required
def course_import_task_result_status_hx(
    request,
    course_import_task_result_id: int,
):
    """
    Get status of a CourseImportTaskResult
    """

    task_result = get_object_or_404(CourseImportTaskResult, id=course_import_task_result_id)
    # Check cache for intermediate progress
    percent_complete = 0
    progress_message = ""
    try:
        cache_key = task_result.progress_cache_key
        status_dict = cache.get(cache_key)
        if status_dict and "percent_complete" in status_dict:
            percent_complete = status_dict["percent_complete"]
            progress_message = status_dict["progress_message"]
        else:
            logger.debug(f"No status in cache with key: {cache_key}")
    except Exception:
        cache_key = None
        logger.exception("course_import_task_result_status_hx() Could not load status from cache ")

    context = {
        "course_import_task_result": task_result,
        "percent_complete": percent_complete,
        "progress_message": progress_message,
    }
    return render(request, "composer/course/hx/course_import_task_result_card.html", context)


@composer_author_required
def edit_course_unit_hx(
    request,
    course_id: int,
    module_node_id: int,
    section_node_id: int,
    unit_node_id: int,
    pk: int,
):
    """
    Builds up an HTMx 'portion' of a composer page with content
    for editing one course unit. The template for this view
    will build an HTMx-based form for each block.

    This view also allows a block to reorder itself (which required
    a complete refresh of this section...that's why we use this 'parent'
    method than the individual block edit methods).

    This function associates each block with a form for editing the block,
    and then returns a list of these pairs to the template for rendering.

    """

    course = get_object_or_404(Course, id=course_id)
    course_unit = get_object_or_404(CourseUnit, id=pk, course=course)

    try:
        module_node = CourseNode.objects.get(id=module_node_id)
        section_node = CourseNode.objects.get(id=section_node_id)
        unit_node = CourseNode.objects.get(id=unit_node_id)
        content_index_label = (
            f"{module_node.content_index}." f"{section_node.content_index}." f"{unit_node.content_index}"
        )
    except Exception:
        module_node = None
        section_node = None
        unit_node = None
        content_index_label = None
        logger.exception("Could not determine content indices")

    show_blocks_collapsed = True
    action = request.GET.get("action", None)
    if action and action == "move_block":
        block_id = request.GET.get("block_id", None)
        direction = request.GET.get("direction", None)
        if not block_id:
            return HttpResponseBadRequest(f"Action is {action} but missing block_id")
        if not direction:
            return HttpResponseBadRequest(f"Action is {action} but missing direction")
        try:
            move_block(course_unit, block_id=int(block_id), direction=direction)
        except Exception:
            logger.exception("Could not move block")
            return HttpResponseBadRequest("Could not move block.")
        show_blocks_collapsed = True

    blocks = course_unit.contents.order_by("unit_blocks__block_order").all()

    context = {
        "title": "Edit Course Unit",
        "block_view_context": BlockViewContext.COMPOSER.name,
        "block_view_mode": BlockViewMode.READ_ONLY.name,
        "course": course,
        "blocks": blocks,
        "course_unit": course_unit,
        "module_slug": module_node.slug,
        "section_slug": section_node.slug,
        "unit_slug": unit_node.slug,
        "unit_node": unit_node,
        "section_node": section_node,
        "module_node": module_node,
        "content_index_label": content_index_label,
        "show_blocks_collapsed": show_blocks_collapsed,
    }

    response = render(request, "composer/course/course_unit_edit.html", context)

    htmx_event = {"editCourseUnit": course_unit.id}
    response["HX-Trigger"] = json.dumps(htmx_event)

    return response


@composer_author_required
def insert_existing_course_unit_block_hx(
    request,
    course_id: int,
    course_unit_id: int,
    module_node_id: int,
    section_node_id: int,
    unit_node_id: int,
):
    """
    Insert an existing block into a course unit.
    """

    block_identifier = request.POST.get("block_identifier", None)
    if not block_identifier:
        return HttpResponseBadRequest("Missing block_identifier")

    course = get_object_or_404(Course, id=course_id)
    course_unit = get_object_or_404(CourseUnit, id=course_unit_id, course=course)

    if course_unit.type != CourseUnitType.STANDARD.name:
        return HttpResponseServerError(f"Cannot add blocks to a CourseUnit of type: {course_unit.type}")

    module_node = get_object_or_404(CourseNode, id=module_node_id)
    section_node = get_object_or_404(CourseNode, id=section_node_id)
    unit_node = get_object_or_404(CourseNode, id=unit_node_id)

    if block_identifier.isnumeric():
        block = Block.objects.get(id=block_identifier)
    else:
        try:
            block = Block.objects.get(slug=block_identifier)
        except Block.DoesNotExist:
            try:
                block = Block.objects.get(uuid=block_identifier)
            except Block.DoesNotExist:
                block = None
            except Block.MultipleObjectsReturned:
                return HttpResponseBadRequest(
                    "More than one blocks correspond to that identifier. " "Try Block ID or block UUID."
                )
        except Block.MultipleObjectsReturned:
            return HttpResponseBadRequest(
                "More than one blocks correspond to that identifier. " "Try Block ID or block UUID."
            )

    if not block:
        raise Http404()

    unit_block = BlockBuilderDirector.insert_existing_block(block=block, course_unit=course_unit)

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

    template = "composer/blocks/block_edit_card_read_only.html"

    response = render(request, template, context)
    htmx_event = {"insertExistingCourseUnitBlock": unit_block.id}

    response["HX-Trigger"] = json.dumps(htmx_event)

    return response


@composer_author_required
def show_add_block_modal_dialog_hx(
    request,
    course_id: int,
    module_node_id: int,
    section_node_id: int,
    unit_node_id: int,
    course_unit_id: int,
):
    course = get_object_or_404(Course, id=course_id)
    course_unit = get_object_or_404(CourseUnit, id=course_unit_id, course=course)

    module_node = get_object_or_404(CourseNode, id=module_node_id)
    section_node = get_object_or_404(CourseNode, id=section_node_id)
    unit_node = get_object_or_404(CourseNode, id=unit_node_id)

    if course_unit.type != CourseUnitType.STANDARD.name:
        return HttpResponseServerError(f"Cannot add blocks to a CourseUnit of type: {course_unit.type}")

    before_block_id = request.GET.get("before_block_id", None)
    if before_block_id:
        before_block_id = int(before_block_id)

    context = {
        "course": course,
        "course_unit": course_unit,
        "module_node": module_node,
        "module_slug": module_node.slug,
        "section_node": section_node,
        "section_slug": section_node.slug,
        "unit_node": unit_node,
        "unit_slug": unit_node.slug,
        "before_block_id": before_block_id,
    }

    response = render(request, "composer/course/dialogs/add_block_modal_dialog.html", context)
    response["HX-Trigger"] = "showAddBlockModal"

    return response


@composer_author_required
def add_course_unit_block_hx(
    request,
    course_id: int,
    module_node_id: int,
    section_node_id: int,
    unit_node_id: int,
    course_unit_id: int,
    block_type: str,
    block_subtype: str = None,
):
    """
    Add a new empty Block to a CourseUnit. The block will be
    built in default configuation. Then the request will be redirected
    to the edit block panel view so that a form is ready for the user
    to configure the block.

    NOTE: This htmx method is usually called from the "Add a New Block" dialog...

    """

    course = get_object_or_404(Course, id=course_id)
    course_unit = get_object_or_404(CourseUnit, id=course_unit_id, course=course)
    module_node = get_object_or_404(CourseNode, id=module_node_id)
    section_node = get_object_or_404(CourseNode, id=section_node_id)
    unit_node = get_object_or_404(CourseNode, id=unit_node_id)

    # VALIDATE
    # incoming args....
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    if course_unit.type != CourseUnitType.STANDARD.name:
        return HttpResponseServerError(f"Cannot add blocks to a CourseUnit of type: {course_unit.type}")

    if block_type not in [item.name for item in BlockType.valid_types_for_composer()]:
        return HttpResponseServerError(f"Cannot add block type : {block_type}")
    elif block_type == BlockType.ASSESSMENT.name:
        if block_subtype not in [item.name for item in AssessmentType]:
            return HttpResponseServerError(f"Invalid ASSESSMENT type : {block_subtype}")
    elif block_type == BlockType.SIMPLE_INTERACTIVE_TOOL.name:
        if block_subtype not in [item.name for item in SimpleInteractiveToolType]:
            return HttpResponseServerError(f"Invalid ASSESSMENT type : {block_subtype}")

    # CREATE BLOCK
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # Determine insert index
    last_index = course_unit.unit_blocks.count()
    insert_index = None
    before_block_id = request.GET.get("before_block_id", None)
    if before_block_id:
        before_block_id = int(before_block_id)
        for ub in course_unit.unit_blocks.all():
            if ub.block.id == before_block_id:
                insert_index = ub.block_order
                break
    else:
        insert_index = last_index

    # Build a new block and unit_block with default configuration
    try:
        block, unit_block = BlockBuilderDirector.build_block(
            block_type=block_type,
            block_subtype=block_subtype,
            course_unit=course_unit,
            insert_index=insert_index,
        )
    except Exception as e:
        logger.exception(f"Could not build block: {e}")
        raise e

    # REDIRECT
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Redirect to the edit block panel view
    redirect_url = reverse(
        "composer:blocks:edit_block_panel_set_hx",
        kwargs={
            "course_id": course.id,
            "module_node_id": module_node.id,
            "section_node_id": section_node.id,
            "unit_node_id": unit_node.id,
            "course_unit_id": course_unit.id,
            "pk": block.id,
        },
    )

    return redirect(redirect_url)


@composer_author_required
def edit_course_nav_hx(request, pk: int):
    course = get_object_or_404(Course, id=pk)

    # Get course nav root node
    root_node = course.course_root_node

    action = request.GET.get("action", None)
    start_at_index = request.GET.get("start_module_index_at", 0)
    start_at_index = int(start_at_index)
    if action == "auto_content_index":
        try:
            root_node.reindex_course_nav_content(start_module_index_at=start_at_index)
        except Exception as e:
            logger.exception("Could not reindex course nav content indices")
            raise e
    elif action == "clear_content_index":
        try:
            root_node.clear_course_nav_content_index()
        except Exception as e:
            logger.exception("Could not clear course nav content indices")
            raise e
    else:
        pass

    delete_course_nav_cache(course_slug=course.slug, course_run=course.run)

    # Get course nav dictionary
    course_nav = get_course_nav(course)
    context = {
        "course": course,
        "course_nav": course_nav,
        "admin_base_url": settings.ADMIN_URL,
    }
    return render(request, "composer/course/course_nav/course_navigation_list.html", context)


@composer_author_required
def delete_module_node_hx(request, course_id: int, pk: int):
    """
    Delete a SECTION node from a MODULE node.
    """
    course = get_object_or_404(Course, id=course_id)
    module_node = get_object_or_404(CourseNode, id=pk)

    if module_node.type != NodeType.MODULE.name:
        return HttpResponseBadRequest("This is not a MODULE node.")

    if module_node.children.exists():
        return HttpResponseBadRequest("Can only delete empty MODULE " "nodes with no SECTIONs.")

    # Delete node itself...
    module_node.delete()

    # Rebuild nav and return...
    delete_course_nav_cache(course.slug, course.run)
    course_nav = get_course_nav(course)
    context = {
        "course": course,
        "course_nav": course_nav,
        "admin_base_url": settings.ADMIN_URL,
    }
    return render(request, "composer/course/course_nav/course_navigation_list.html", context)


@composer_author_required
def delete_section_node_hx(request, course_id: int, module_node_id: int, pk: int):
    """
    Delete a SECTION node from a MODULE node.
    """
    course = get_object_or_404(Course, id=course_id)
    section_node = get_object_or_404(CourseNode, id=pk)

    if section_node.type != NodeType.SECTION.name:
        return HttpResponseBadRequest("This is not a SECTION node.")

    if section_node.children.exists():
        return HttpResponseBadRequest("Can only delete empty SECTION " "nodes with no UNITs.")

    # Delete node itself...
    section_node.delete()

    # Rebuild nav and return...
    delete_course_nav_cache(course.slug, course.run)
    course_nav = get_course_nav(course)
    context = {
        "course": course,
        "course_nav": course_nav,
        "admin_base_url": settings.ADMIN_URL,
    }
    return render(request, "composer/course/course_nav/course_navigation_list.html", context)


@composer_author_required
def delete_unit_node_hx(request, course_id: int, module_node_id: int, section_node_id: int, pk: int):
    """
    Delete a unit node from a section node.
    """
    course = get_object_or_404(Course, id=course_id)
    # module_node = get_object_or_404(CourseNode, id=module_node_id)
    # section_node = get_object_or_404(CourseNode, id=section_node_id)
    unit_node = get_object_or_404(CourseNode, id=pk)

    if unit_node.type != NodeType.UNIT.name:
        return HttpResponseBadRequest("This is not a UNIT node.")

    # Delete attached CourseUnit if this is its only parent...
    course_unit: Optional[CourseUnit] = unit_node.unit
    if course_unit and course_unit.course_nodes.count() == 1:
        # If this node is the CourseUnit's only parent, delete it too.
        course_unit.delete()

    # Delete node itself...
    unit_node.delete()

    # Rebuild nav and return...
    delete_course_nav_cache(course.slug, course.run)
    course_nav = get_course_nav(course)
    context = {
        "course": course,
        "course_nav": course_nav,
        "admin_base_url": settings.ADMIN_URL,
    }
    return render(request, "composer/course/course_nav/course_navigation_list.html", context)


@composer_author_required
def add_module_to_root_node_hx(request, pk: int):
    """
    Adds a new MODULE node to a ROOT node and
    places at the end of the course node list.
    """
    course = get_object_or_404(Course, id=pk)
    root_node: CourseNode = course.course_root_node

    module_node = create_module_node(root_node=root_node)
    logger.info(f"Created module node: {module_node}")

    # Rebuild nav and return...
    delete_course_nav_cache(course.slug, course.run)
    course_nav = get_course_nav(course)
    context = {
        "course": course,
        "course_nav": course_nav,
        "admin_base_url": settings.ADMIN_URL,
    }
    return render(request, "composer/course/course_nav/course_navigation_list.html", context)


@composer_author_required
def add_section_node_to_module_hx(request, course_id: int, module_node_id: int):
    """
    Adds a new Unit node to a Section node and
    places at the end of the Section.
    Create a CourseUnit for this Unit node.
    """
    course = get_object_or_404(Course, id=course_id)
    module_node = get_object_or_404(CourseNode, id=module_node_id)

    section_node = create_section_node(module_node=module_node)
    logger.info(f"Created section node: {section_node}")

    # Rebuild nav and return...
    delete_course_nav_cache(course.slug, course.run)
    course_nav = get_course_nav(course)
    context = {
        "course": course,
        "course_nav": course_nav,
        "admin_base_url": settings.ADMIN_URL,
    }
    return render(request, "composer/course/course_nav/course_navigation_list.html", context)


@composer_author_required
def add_unit_to_section_hx(request, course_id: int, module_node_id: int, section_node_id: int):
    """
    Adds a new Unit node to a Section node and
    places at the end of the Section.
    Create a CourseUnit for this Unit node.
    """
    course = get_object_or_404(Course, id=course_id)
    # module_node = get_object_or_404(CourseNode, id=module_node_id)
    section_node = get_object_or_404(CourseNode, id=section_node_id)

    # Add a new Unit Node and CourseUnit
    unit_node = create_unit_node(course=course, section_node=section_node)
    logger.info(f"Created section node: {unit_node}")

    # Rebuild nav and return...
    delete_course_nav_cache(course.slug, course.run)
    course_nav = get_course_nav(course)
    context = {
        "course": course,
        "course_nav": course_nav,
        "admin_base_url": settings.ADMIN_URL,
    }
    return render(request, "composer/course/course_nav/course_navigation_list.html", context)


@composer_author_required
def toggle_wysiwyg_hx(request):
    """
    Toggle the composer wysiwyg editor on or off.
    """

    composer_settings, created = ComposerSettings.objects.get_or_create(user=request.user)
    composer_settings.wysiwyg_active = not composer_settings.wysiwyg_active

    context = {
        "wysiwyg_active": composer_settings.wysiwyg_active,
    }

    if composer_settings.wysiwyg_active:
        toggle_message = "WYSIWYG editor is now active."
    else:
        toggle_message = "WYSIWYG editor is now inactive."

    response = render(request, "composer/hx/toggle_wysiwyg.html", context)

    # Ask the toast to show a message...
    htmx_message = {"showMessage": toggle_message}
    response["HX-Trigger"] = json.dumps(htmx_message)

    return response


# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# HELPER METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~


def load_course_from_form(form) -> Course:
    """
    Load course from Composer (simple) form.
    Raise an exception if load goes bad for some reason.

    Args:
        form:   A Form instance with course json submitted by user.

    Returns:
        A course instance

    """

    if not form.is_valid():
        raise Exception("Form is not valid.")

    course_jsons = form.cleaned_data["course_json"]
    try:
        course_json = json.loads(course_jsons)
    except Exception as e:
        raise Exception("Could not read json.") from e

    # Check for metadata. For now, we just report to command line log.
    document_type = course_json.get("document_type")
    if document_type:
        if document_type not in VALID_COURSE_EXPORT_FORMAT_IDS:
            raise Exception(f"Invalid document type: {document_type}")
        metadata = course_json.get("metadata", {})
        exporter_version = metadata.get("exporter_version", None)
        export_date = metadata.get("export_date", None)
        logger.info(
            f"Importing a course exported by KinesinLMS Composer. "
            f"Composer exporter version : {exporter_version}. "
            f"Export Date: {export_date} "
        )
        course_json = course_json.get("course", None)

    # Make sure course doesn't already exist
    slug = course_json.get("slug")
    run = course_json.get("run")
    try:
        Course.objects.get(slug=slug, run=run)
        raise Exception(f"Course {slug}_{run} already exists. " f"Please delete before loading again.")
    except Course.DoesNotExist:
        # All good to create a new course with this slug and run!
        pass

    try:
        importer = KinesinLMSCourseImporter()
        with transaction.atomic():
            course = importer.import_course_from_json(course_json)
    except Exception as e:
        error_message = f"Could not load course from JSON: {e}"
        logger.exception(error_message)
        raise Exception(error_message) from e

    # After import, save every Block in this course again
    # to make sure that the search_vector was set.
    # I can't figure out why, but it's not getting set
    # via the post_save signal during course import...perhaps
    # something to do with transactions during deserializing
    try:
        unit_blocks = UnitBlock.objects.filter(course_unit__course=course).all()
        for unit_block in unit_blocks:
            if unit_block.block.type == BlockType.VIDEO.name:
                # This should kick off post_save handler...
                unit_block.block.save()
    except Exception:
        logger.exception("Could not do post transaction saves of Block objects.")

    return course


def move_block(course_unit: CourseUnit, block_id: int, direction: str) -> Optional[int]:
    """
    Move a block in the unit_blocks sequence.

    Returns:
        New index if moved, otherwise None
    """
    if direction not in ["UP", "DOWN"]:
        raise ValueError(f"move_block(): Invalid direction : {direction}")

    unit_blocks = course_unit.unit_blocks.all().order_by("block_order")

    last_index = unit_blocks.count() - 1
    for index, unit_block in enumerate(unit_blocks):
        if unit_block.block.id == block_id:
            if index == 0 and direction == "UP":
                return None
            if index == last_index and direction == "DOWN":
                return None
            if direction == "UP":
                unit_block.block_order = unit_block.block_order - 1
                unit_block.save()
                prev_unit_block = unit_blocks[index - 1]
                prev_unit_block.block_order = prev_unit_block.block_order + 1
                prev_unit_block.save()
                return unit_block.block_order
            if direction == "DOWN":
                unit_block.block_order = unit_block.block_order + 1
                unit_block.save()
                next_unit_block = unit_blocks[index + 1]
                next_unit_block.block_order = next_unit_block.block_order - 1
                next_unit_block.save()
                return unit_block.block_order
    return None
