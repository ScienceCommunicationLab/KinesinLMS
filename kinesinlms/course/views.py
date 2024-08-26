import json
from typing import Dict, List, Optional
import logging
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchHeadline, SearchRank
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models.functions import Concat
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, resolve_url
from django.shortcuts import redirect
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import get_template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import QuerySet
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext as _

from rest_framework import viewsets, status
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.db.models import TextField

from kinesinlms.badges.models import BadgeAssertion, BadgeClass, BadgeClassType
from kinesinlms.catalog.service import do_enrollment
from kinesinlms.certificates.models import CertificateTemplate, Certificate
from kinesinlms.certificates.service import CertificateTemplateFactory
from kinesinlms.course.certificates.generators import generate_base_certificate, generate_custom_certificate
from kinesinlms.course.custom_views.views import get_custom_unit_data, get_custom_unit_template
from kinesinlms.course.models import Course, CourseNode, CoursePassed, CourseUnit, Block, BlockType, CourseUnitType, Bookmark, Enrollment, Milestone, MilestoneProgress, Notice, NoticeType
from kinesinlms.course.nav import get_course_nav, CourseNavException, get_first_course_page_url
from kinesinlms.course.progress import get_progress_status
from kinesinlms.course.serializers import BookmarkSerializer, CourseNodeSimpleSerializer, CourseMetaSerializer, \
    CourseSerializer
from kinesinlms.course.utils import get_student_cohort, user_is_enrolled
from kinesinlms.course.utils_access import can_access_course, UnitNavInfo, get_unit_nav_info, ModuleNodeNotReleased, \
    SectionNodeNotReleased, ModuleNodeDoesNotExist, SectionNodeDoesNotExist, UnitNodeDoesNotExist
from kinesinlms.course.view_helpers import access_denied_page, process_course_hx_request
from kinesinlms.custom_app.models import CustomApp, CustomAppTypes
from kinesinlms.custom_app.views import course_speakers, peer_review_journal, simple_html_content
from kinesinlms.forum.models import ForumCategory, ForumSubcategory, \
    ForumSubcategoryType, ForumTopic
from kinesinlms.forum.service.base_service import BaseForumService
from kinesinlms.forum.utils import get_forum_service, get_forum_provider
from kinesinlms.learning_library.constants import BlockViewContext, ResourceType
from kinesinlms.learning_library.models import BlockResource, UnitBlock, Resource
from kinesinlms.learning_library.utils import get_learning_objectives
from kinesinlms.sits.models import SimpleInteractiveTool
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.tracker import Tracker
from kinesinlms.course.models import CourseResource

logger = logging.getLogger(__name__)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# API
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CourseViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for listing or retrieving basic course data.
    Course 'meta' is really just Course model data.

    This API is meant only for admins or applications like dashboard
    that should have admin status.

    """

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]

    def list(self, request):
        queryset = Course.objects.all()
        serializer = CourseMetaSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = Course.objects.all()
        course = get_object_or_404(queryset, pk=pk)
        serializer = CourseSerializer(course)
        return Response(serializer.data)

    @action(detail=True,
            methods=['get'],
            name='Course Assessments and Activities')
    def interactive_elements(self, request, pk):
        """
        Lists interactive elements within navigational context.
        This is important for things like analytics that needs to
        know where Assessments and SITs appear in a course.

        Blocks are only written once, regardless of how many times they
        appear in the course.

        """
        course = get_object_or_404(Course, pk=pk)

        # Build a simple nav structure with Assessments and SITs in context
        block_ids = []
        assessments_data = []
        sits_data = []
        module_nodes = course.course_root_node.children.all()
        for module_node in module_nodes:
            for section_node in module_node.children.all():
                for unit_node in section_node.children.all():
                    course_unit = unit_node.unit
                    for unit_block in course_unit.unit_blocks.all():
                        if unit_block.block.type not in [BlockType.ASSESSMENT.name,
                                                         BlockType.SIMPLE_INTERACTIVE_TOOL.name]:
                            continue
                        block = unit_block.block
                        if unit_block.block.id in block_ids or unit_block.read_only:
                            continue
                        block_ids.append(block.id)
                        data = {
                            "module_id": module_node.id,
                            "module_content_index": module_node.content_index,
                            "section_id": section_node.id,
                            "section_content_index": section_node.content_index,
                            "unit_id": unit_node.id,
                            "unit_content_index": unit_node.content_index,
                            "unit_block_index_label": unit_block.index_label,
                            "unit_block_slug": unit_block.slug,
                            "block_id": block.id,
                            "block_slug": block.slug
                        }
                        if block.type == BlockType.ASSESSMENT.name:
                            data['graded'] = block.assessment.graded
                            data['assessment_id'] = block.assessment.id
                            data['assessment_slug'] = block.assessment.slug
                            assessments_data.append(data)
                        elif block.type == BlockType.SIMPLE_INTERACTIVE_TOOL.name:
                            data['graded'] = block.simple_interactive_tool.graded
                            data['sit_id'] = block.simple_interactive_tool.id
                            data['sit_slug'] = block.simple_interactive_tool.slug
                            sits_data.append(data)

        data = {
            "course_id": course.id,
            "assessments": assessments_data,
            "sits": sits_data
        }
        return Response(data=data)


# noinspection PyUnusedLocal
class CourseNavViewSet(viewsets.ViewSet):
    """
    Generates the JSON that describes the course navigation.
    This isn't current used at the moment, but could be used
    by the client if we move to having React-style components
    build the nav after an API call.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request):
        response = {'message': 'Create function is not offered in this path.'}
        return Response(response, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, pk=None):
        response = {'message': 'Update function is not offered in this path.'}
        return Response(response, status=status.HTTP_403_FORBIDDEN)

    def partial_update(self, request, pk=None):
        response = {'message': 'Update function is not offered in this path.'}
        return Response(response, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, pk=None):
        response = {'message': 'Delete function is not offered in this path.'}
        return Response(response, status=status.HTTP_403_FORBIDDEN)

    def list(self, request, pk=None):
        response = {'message': 'List function is not offered in this path.'}
        return Response(response, status=status.HTTP_403_FORBIDDEN)

    @method_decorator(cache_page(60 * 60 * 2))
    def retrieve(self, request, pk=None):
        """
        Gets a json representation of the course nav. Important to cache since
        this is a bit intensive to produce.
        """
        queryset = Course.objects.all()
        course = get_object_or_404(queryset, pk=pk)
        serializer = CourseNodeSimpleSerializer(course.course_root_node)
        return Response(serializer.data)


class BookmarkViewSet(viewsets.ModelViewSet):
    """
    Generates the JSON describing a student's bookmarks in the course.
    """
    serializer_class = BookmarkSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self, *args, **kwargs):
        if self.request.user.is_superuser:
            return Bookmark.objects.all()
        else:
            return Bookmark.objects.all().filter(student=self.request.user)

    # TODO: Implement these
    def partial_update(self, request, *args, pk=None, **kwargs):
        response = {'message': 'Update function is not offered in this path.'}
        return Response(response, status=status.HTTP_403_FORBIDDEN)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# VIEW METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# TEMPLATE VIEW METHODS
# ...................................


@login_required
def course_home_page(request, course_slug=None, course_run=None):
    """
    Given course and run, show course home page. This is the first tab
    in the list of tabs in the course view. It shows top-level info about the
    course, provides links to the syllabus, etc.

    Args:
        request:
        course_slug:
        course_run:
    """

    # TODO: Refactor to use AccessService

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    enrollment = get_object_or_404(Enrollment,
                                   student=request.user,
                                   course=course,
                                   active=True)

    if not can_access_course(user=request.user,
                             course=course,
                             enrollment=enrollment):
        return access_denied_page(request=request, course_slug=course_slug, course_run=course_run)
    if enrollment.enrollment_survey_required:
        enrollment_survey_url = reverse('catalog:enrollment_survey', kwargs={'course_slug': course.slug,
                                                                             'course_run': course.run})
        return redirect(enrollment_survey_url)

    course_home_template_path = f"course/home/{course_slug}/{course_run}/home.html"

    try:
        get_template(course_home_template_path)
    except TemplateDoesNotExist:
        course_home_template_path = "course/home/default_home.html"

    course_notices_qs = Notice.objects.filter(course=course)

    news_items = course_notices_qs.filter(type=NoticeType.NEWS_ITEM.name).all()
    important_dates = course_notices_qs.filter(type=NoticeType.IMPORTANT_DATE.name).all()
    course_resources = course.course_resources.all()

    first_unit_url = f"/courses/{course_slug}/{course_run}/content/"

    context = {
        "course": course,
        "current_course_tab": "home",
        "current_course_tab_name": "Home",
        "news": news_items,
        "course_resources": course_resources,
        "important_dates": important_dates,
        "first_unit_url": first_unit_url
    }

    Tracker.track(event_type=TrackingEventType.COURSE_HOME_VIEW.value,
                  user=request.user,
                  event_data={'page': "home"},
                  course=course,
                  unit_node_slug=None,
                  course_unit_id=None,
                  course_unit_slug=None,
                  block_uuid=None)

    return render(request, course_home_template_path, context)


@login_required
def redirect_to_unit_page(request, course_slug, course_run, module_slug=None, section_slug=None):
    """
    Given course and run, and potentially module and section,
    redirect to the correct URL for the first Unit available,
    or if the user has visited the course before,
    look for the last unit visited and try to go there.

    Args:
        request:
        course_slug:
        course_run:
        module_slug:
        section_slug:

    Returns:
        Redirect to a valid module/section/unit url.
    """

    assert course_slug is not None
    assert course_run is not None

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course, active=True)
    if not can_access_course(user=request.user, course=course, enrollment=enrollment):
        return access_denied_page(request=request, course_slug=course_slug, course_run=course_run)
    if enrollment.enrollment_survey_required:
        enrollment_survey_url = reverse('catalog:enrollment_survey', kwargs={'course_slug': course.slug,
                                                                             'course_run': course.run})
        return redirect(enrollment_survey_url)

    # If no module, section or unit, look for a last viewed unit path
    redirect_url = None
    if not module_slug:
        cookie_name = f"{course.token}_last_viewed_unit_id"
        last_viewed_unit_id = request.COOKIES.get(cookie_name, None)
        # This message might be overkill so disabling for now...
        # messages.add_message(request,  messages.INFO, "Jumped to where you left off in the course...")
        redirect_url = None
        if last_viewed_unit_id:
            try:
                unit: CourseNode = CourseNode.objects.get(id=int(last_viewed_unit_id))
                is_released = unit.is_released and unit.parent.is_released and unit.parent.parent.is_released
                if is_released or request.user.is_superuser or request.user.is_staff:
                    redirect_url = unit.node_url
                else:
                    # Don't do a redirect. Unit isn't released.
                    pass
            except Exception:
                logger.exception(f"Tried to use last_viewed_unit_id {last_viewed_unit_id} in session "
                                 f"to get the unit CourseNode, but got error instead. Redirecting "
                                 f"user to first unit...")
                redirect_url = None

    if not redirect_url:
        # Use doesn't have a previous session with a unit view. So find the first unit in the course.
        # By definition, there has to be at least one module, with one section,
        # with one unit. Otherwise, the course isn't constructed right. Get the first module
        # section or unit if user didn't provide a slug for it.
        try:
            if module_slug:
                module_node = course.course_root_node.get_children().filter(slug=module_slug).first()
                if not module_node:
                    msg = _("No such module: ")
                    raise Http404(f"{msg}{module_slug}")
            else:
                module_node = course.course_root_node.get_children().first()

            if section_slug:
                section_node = module_node.get_children().filter(slug=section_slug).first()
                if not section_node:
                    msg = _("No such section: ")
                    raise Http404(f"{msg}{section_slug}")
            else:
                section_node = module_node.get_children().first()

            unit_node = section_node.get_children().first()

            redirect_url = unit_node.node_url
        except Exception:
            logger.exception(f"Could not generate redirect_url for {course.token} from "
                             f"module_slug {module_slug} and section_slug {section_slug}.")
            raise Http404(_("Not a valid course content url."))

    return redirect(redirect_url)


@ensure_csrf_cookie
@login_required
def block_page(request,
               course_slug=None,
               course_run=None,
               module_slug=None,
               section_slug=None,
               unit_slug=None,
               block_id=None):
    """
    Show a block of a course by itself, rather than as part
    of a course unit.
    """

    # TODO: Refactor to use AccessService

    if course_slug is None:
        raise ValueError('course_slug cannot be None')
    if course_run is None:
        raise ValueError('course_run cannot be None')
    if module_slug is None:
        raise ValueError('module_slug cannot be None')
    if section_slug is None:
        raise ValueError('section_slug cannot be None')
    if unit_slug is None:
        raise ValueError('unit_slug cannot be None')
    if block_id is None:
        raise ValueError('unit_slug cannot be None')

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    if request.user.is_superuser or request.user.is_staff:
        # A superuser or staff can view a course block without being enrolled
        is_beta_tester = False
        show_admin_controls = request.session.get('show_admin_controls', True)
    else:
        enrollment = get_object_or_404(Enrollment, student=request.user, course=course, active=True)
        if not can_access_course(request.user, course, enrollment=enrollment):
            return access_denied_page(request=request, course_slug=course_slug, course_run=course_run)
        if enrollment.enrollment_survey_required:
            return redirect('catalog:enrollment_survey', kwargs={'course_slug': course.slug,
                                                                 'course_run': course.run})
        is_beta_tester = enrollment.beta_tester
        show_admin_controls = False

    # Get dictionary for nav
    try:
        course_nav: Dict = get_course_nav(course, is_beta_tester=is_beta_tester)
    except CourseNavException as cne:
        logger.exception(f"unit_page():  Could not generate course {course} navigation with "
                         f"call to get_course_nav()")
        raise Exception("Internal error. Please contact support for help.") from cne

    try:
        unit_nav_info: UnitNavInfo = get_unit_nav_info(course_nav,
                                                       module_node_slug=module_slug,
                                                       section_node_slug=section_slug,
                                                       unit_node_slug=unit_slug,
                                                       self_paced=course.self_paced,
                                                       is_staff=request.user.is_staff,
                                                       is_superuser=request.user.is_superuser)
    except ModuleNodeDoesNotExist:
        raise Http404(_("Module does not exist"))
    except SectionNodeDoesNotExist:
        raise Http404(_("Section does not exist"))
    except UnitNodeDoesNotExist:
        raise Http404(_("Unit does not exist"))
    except Exception:
        logger.exception("Could not build nav info")
        raise Http404(_("No unit found."))

    # See if we have to prevent viewing
    admin_message = None
    if not unit_nav_info.unit_node_released:
        if request.user.is_superuser or request.user.is_staff:
            admin_message = "The unit for this block is not yet available to students (Unit not released)."
        else:
            msg = _("Unit is not yet released. Release date: ")
            raise Http404(f"{msg}{unit_nav_info.module_release_datetime}")
    if not unit_nav_info.section_released:
        if request.user.is_superuser or request.user.is_staff:
            admin_message = _("The unit for this block is not yet available to students (Section not released).")
        else:
            msg = _("Section is not yet released. Release date: ")
            raise Http404(f"{msg}{unit_nav_info.module_release_datetime}")
    if not unit_nav_info.module_released:
        if request.user.is_superuser or request.user.is_staff:
            admin_message = _("The unit for this block is not yet available to students (Module not released).")
        else:
            msg = _("Module is not yet released. Release date: ")
            raise Http404(f"{msg}{unit_nav_info.module_release_datetime}")

    # Get CourseNode
    try:
        current_unit_node = CourseNode.objects.get(id=unit_nav_info.unit_node_id)
    except Exception:
        # Even though we have the ID of a 'UNIT' CourseNode ID in the cached nav...we don't have an
        # actual instance of this node with that ID in the database.
        logger.error(f"Could not find CourseNode with id {unit_nav_info.unit_node_id}")
        raise Http404(_("No unit found."))

    # Get CourseUnit
    try:
        course_unit = current_unit_node.unit
        if not course_unit:
            raise Exception("Missing unit")
    except Exception:
        raise Http404(_("Course is missing this unit."))

    # Get block
    try:
        block = course_unit.contents.get(id=block_id)
    except Block.DoesNotExist:
        raise Http404(f"Block {block_id} does not exist in this unit")

    extra_course_unit_js_libraries = []

    # Add extra content based on block
    if block.type == BlockType.SIMPLE_INTERACTIVE_TOOL.name:
        tool_type = block.simple_interactive_tool.tool_type
        js_libraries = SimpleInteractiveTool.get_helper_javascript_libraries(tool_type)
        for js_library in js_libraries:
            if js_library not in extra_course_unit_js_libraries:
                extra_course_unit_js_libraries.append(js_library)

    cohort = get_student_cohort(course=course, student=request.user)

    context = {
        "current_block": block,
        "course_unit": course_unit,
        "module_slug": module_slug,
        "section_slug": section_slug,
        "unit_slug": unit_slug,
        "admin_message": admin_message,
        "course": course,
        "course_name": course.display_name,
        "cohort": cohort,
        "is_beta_tester": is_beta_tester,
        "extra_course_unit_js_libraries": extra_course_unit_js_libraries,
        "show_admin_controls": show_admin_controls
    }

    response = render(request, "course/standalone_block.html", context)

    return response


# DMcQ: We need @ensure_csrf_cookie to make sure Django writes csrf cookie, because
# any React components need it, but Django won't write it
# if no regular Django forms are contained in the view.
@ensure_csrf_cookie
@login_required
def unit_page(request,
              course_slug=None,
              course_run=None,
              module_slug=None,
              section_slug=None,
              unit_slug=None):
    """
    Show a unit page of a course. The module, section and unit slugs correspond
    to CourseNodes in the MPTT tree. (The unit_slug is the slug on the CourseNode object,
    *not* the Block object it refers to.)

    Requests arriving to this view *must* have module, section and unit slugs set.
    (Partial urls will already have been figured out in redirect_to_unit_page.)

    TODO:
        Since we're using HTMx more now, there's really no reason to do a
        full page reload when a user clicks on a unit. We should just load the
        unit content with HTMx. This would improve responsiveness.

    """

    # TODO: Refactor to use AccessService

    if course_slug is None:
        raise ValueError('course_slug cannot be None')
    if course_run is None:
        raise ValueError('course_run cannot be None')
    if module_slug is None:
        raise ValueError('module_slug cannot be None')
    if section_slug is None:
        raise ValueError('section_slug cannot be None')
    if unit_slug is None:
        raise ValueError('unit_slug cannot be None')

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    try:
        enrollment = Enrollment.objects.get(student=request.user, course=course, active=True)
    except Enrollment.DoesNotExist:
        if request.user.is_superuser:
            # A superuser can view a course without being enrolled.
            # However, we autoenroll if not, to make sure everything works as expected.
            enrollment = do_enrollment(user=request.user, course=course)
        else:
            # This user is a regular student, an educator or staff.
            # These types of users have to enroll.
            return access_denied_page(request=request, course_run=course.run, course_slug=course.slug)

    if not can_access_course(request.user, course, enrollment=enrollment):
        return access_denied_page(request=request, course_slug=course.slug, course_run=course.run)
    if enrollment.enrollment_survey_required:
        return redirect('catalog:enrollment_survey', kwargs={'course_slug': course.slug,
                                                             'course_run': course.run})
    is_beta_tester = enrollment.beta_tester

    try:
        course_nav: Dict = get_course_nav(course, is_beta_tester=is_beta_tester)
    except CourseNavException as cne:
        logger.exception(f"unit_page():  Could not generate course {course} navigation with "
                         f"call to get_course_nav()")
        raise Exception(_("Internal error. Please contact support for help.")) from cne

    # CONSTRUCT NAV INFORMATION WITH FLAGS FOR 'ACTIVE', IS_RELEASED, ETC.
    # Get active node information, is_released and next / prev information from
    # the generated courses_nav dictionary.
    # In this section we try to do all our nav meta-data setup with no db calls.
    # Rather, we just use the dictionary created by the serializer in get_course_nav()
    #
    # Remember that CourseNode slugs do not have to be unique, so we have to be
    # careful about remembering parent and child relationships when we're using slugs
    # to look up CourseNode id.

    # Generate prev and next unit information and unit release information.
    # Handle exceptions and show 404 if module or section node does
    # not exist or isn't released.
    # NOTE: It is NOT an exception if the unit is not released
    # as we want get_unit_nav_info to return prev and next information.
    # In that case, the UnitNavInfo instance will be returned and will have information about unit release date.
    try:
        unit_nav_info: UnitNavInfo = get_unit_nav_info(course_nav,
                                                       module_node_slug=module_slug,
                                                       section_node_slug=section_slug,
                                                       unit_node_slug=unit_slug,
                                                       self_paced=course.self_paced,
                                                       is_staff=request.user.is_staff,
                                                       is_superuser=request.user.is_superuser)
    except ModuleNodeDoesNotExist:
        raise Http404(_("Module does not exist"))
    except SectionNodeDoesNotExist:
        raise Http404(_("Section does not exist"))
    except UnitNodeDoesNotExist:
        raise Http404(_("Unit does not exist"))
    except Exception:
        logger.exception("Could not build nav info")
        raise Http404(_("No unit found."))

    # See if we have to prevent viewing
    admin_message = None
    if not unit_nav_info.unit_node_released:
        if request.user.is_superuser or request.user.is_staff:
            admin_message = "This unit is not yet available to students (Unit not released)."
        else:
            # If unit is not yet released, the template will
            # handle showing the right information
            pass
    if not unit_nav_info.section_released:
        if request.user.is_superuser or request.user.is_staff:
            admin_message = "This unit is not yet available to students (Section not released)."
        else:
            raise Http404(f"Section is not yet released. Release date: {unit_nav_info.module_release_datetime}")
    if not unit_nav_info.module_released:
        if request.user.is_superuser or request.user.is_staff:
            admin_message = "This unit is not yet available to students (Module not released)."
        else:
            raise Http404(f"Module is not yet released. Release date: {unit_nav_info.module_release_datetime}")

    # Set release information
    if course.self_paced:
        unit_is_released = True
        unit_release_datetime = None
    else:
        unit_is_released = unit_nav_info.unit_node_released
        unit_release_datetime = unit_nav_info.unit_node_release_datetime

    # Init some variables...
    current_unit_node: Optional[CourseNode] = None
    course_unit: Optional[CourseUnit] = None
    bookmark_info = {}
    custom_unit_data = None
    blocks: Optional[QuerySet] = None
    extra_course_unit_js_libraries: List[str] = []
    unit_template = 'course/unit.html'

    if unit_is_released:
        # Get CourseNode
        try:
            current_unit_node = CourseNode.objects.get(id=unit_nav_info.unit_node_id)
        except Exception:
            # Even though we have the ID of a 'UNIT' CourseNode ID in the cached nav...we don't have an
            # actual instance of this node with that ID in the database.
            logger.error(f"Could not find CourseNode with id {unit_nav_info.unit_node_id}")
            raise Http404(_("No unit found."))

        # Get CourseUnit
        try:
            course_unit = current_unit_node.unit
            if not course_unit:
                raise Exception("Missing unit")
        except Exception:
            raise Http404("Course is missing this unit.")

        # Get Bookmark info
        bookmark_info = {
            "unit_node_id": current_unit_node.id,
            "course_id": course.id
        }
        try:
            bookmark = Bookmark.objects.get(unit_node=current_unit_node, student=request.user)
            bookmark_info["bookmark_id"] = bookmark.id
        except Bookmark.MultipleObjectsReturned:
            # This shouldn't happen. Delete all but one and return that.
            bookmarks = Bookmark.objects.filter(unit_node=current_unit_node, student=request.user).all()
            for index, bookmark in enumerate(bookmarks):
                if index == 0:
                    continue
                else:
                    bookmark.delete()

        except Bookmark.DoesNotExist:
            pass

        # Get blocks or custom content...
        if course_unit.type in [CourseUnitType.STANDARD.name, CourseUnitType.ROADMAP.name]:
            blocks = course_unit.contents.filter(unit_blocks__hide=False).order_by('unit_blocks__block_order')
            # blocks = course_unit.contents.all().order_by('unit_blocks__block_order')
            # Standard unit so use defaults and load nodes.
        elif course_unit.type in [CourseUnitType.SECTION_LEARNING_OBJECTIVES.name,
                                  CourseUnitType.MODULE_LEARNING_OBJECTIVES.name]:
            pass
        else:
            # this is a custom course_unit so get appropriate template and data.
            custom_unit_data = get_custom_unit_data(request, course=course, course_unit=course_unit)
            unit_template = get_custom_unit_template(course=course, course_unit=course_unit)

        # Get custom interactive tools...
        # Check for react component usage. Later we may build a more sophisticated approach
        # to deciding which React component libraries to include.
        extra_course_unit_js_libraries = []
        if blocks:
            sit_blocks = blocks.filter(type=BlockType.SIMPLE_INTERACTIVE_TOOL.name)
            if sit_blocks.count() > 0:
                for sit_block in sit_blocks:
                    tool_type = sit_block.simple_interactive_tool.tool_type
                    js_libraries = SimpleInteractiveTool.get_helper_javascript_libraries(tool_type)
                    for js_library in js_libraries:
                        if js_library not in extra_course_unit_js_libraries:
                            extra_course_unit_js_libraries.append(js_library)
    else:
        # No content as unit is not yet released
        unit_release_datetime = unit_nav_info.unit_node_release_datetime

    try:
        # DMcQ: Weird bug where more than one bookmark was getting created for a unit_node and user,
        # DMcQ: so have to use filter rather than get.
        bookmark = Bookmark.objects.filter(unit_node=current_unit_node, student=request.user).first()
        if bookmark:
            bookmark_info["bookmark_id"] = bookmark.id
    except Exception:
        logger.exception(f"Could not get bookmark. Unit_node: {current_unit_node}. ")
        pass

    # For now, every course should have an override css, even if empty.
    # CSS is for all courses, regardless of run
    # (Later maybe add a boolean or even custom css name to model.)
    course_custom_css_filename = f"{course.slug}.css"

    # Admin extras
    admin_edit_url = None
    show_admin_controls = False
    if request.user.is_superuser or request.user.is_staff:
        # If course isn't released we won't have looked up unit
        # but this is an admin so look it up, so we can link to it.
        if not course_unit:
            current_unit_node: CourseNode = CourseNode.objects.get(id=unit_nav_info.unit_node_id)
            course_unit = current_unit_node.unit
        admin_edit_url = f"/{settings.ADMIN_URL}course/courseunit/{course_unit.id}/change/"
        show_admin_controls = request.session.get('show_admin_controls', True)

    # Cohort
    cohort = get_student_cohort(course=course, student=request.user)

    # Learning objectives
    learning_objectives = []
    if course_unit:
        try:
            learning_objectives = get_learning_objectives(course_unit=course_unit,
                                                          current_unit_node=current_unit_node)
        except Exception:
            logger.exception("Could not load learning objectives")

    if hasattr(course_unit, 'unit_blocks'):
        unit_blocks = course_unit.unit_blocks.all()
    else:
        unit_blocks = []

    # CONTEXT
    # Build up context for template...
    context = {
        "course": course,
        "cohort": cohort,
        "course_nav": course_nav,
        "course_name": course.display_name,
        "course_unit": course_unit,
        "unit_blocks": unit_blocks,
        "custom_unit_data": custom_unit_data,
        "bookmark_info": bookmark_info,
        "current_course_tab": "course",
        "current_course_tab_name": "Course",
        "admin_edit_url": admin_edit_url,
        "course_custom_css_filename": course_custom_css_filename,
        "learning_objectives": learning_objectives,
        "admin_message": admin_message,
        "module_slug": module_slug,
        "section_slug": section_slug,
        "unit_slug": unit_slug,

        # Block info...
        "block_view_context": BlockViewContext.COURSE.name,

        # release information...
        "unit_is_released": unit_is_released,
        "unit_release_datetime": unit_release_datetime,

        # nav/node information...
        "full_content_index": unit_nav_info.full_content_index,
        "unit_node_slug": unit_nav_info.unit_node_slug,
        "current_unit_node_id": unit_nav_info.unit_node_id,
        "prev_unit_node_url": unit_nav_info.prev_unit_node_url,
        "prev_unit_node_name": unit_nav_info.prev_unit_node_name,
        "next_unit_node_url": unit_nav_info.next_unit_node_url,
        "next_unit_node_name": unit_nav_info.next_unit_node_name,
        "active_module_node_id": unit_nav_info.module_node_id,
        "active_module_node_display_name": unit_nav_info.module_node_display_name,
        "active_section_node_id": unit_nav_info.section_node_id,
        "active_section_node_display_name": unit_nav_info.section_node_display_name,
        "active_unit_node_id": unit_nav_info.unit_node_id,
        "unreleased_content": unit_nav_info.unreleased_content,

        # javascript libraries..
        "extra_course_unit_js_libraries": extra_course_unit_js_libraries,

        # Admin controls
        "show_admin_controls": show_admin_controls

    }

    if unit_is_released:
        # Track activity
        Tracker.track(event_type=TrackingEventType.COURSE_PAGE_VIEW.value,
                      user=request.user,
                      event_data={"unit_display_name": course_unit.display_name},
                      course=course,
                      unit_node_slug=current_unit_node.slug,
                      course_unit_id=course_unit.id,
                      course_unit_slug=course_unit.slug,
                      block_uuid=None)

    # Generate response (finally!)
    response = render(request, unit_template, context)

    # Save user's place for next session
    try:
        cookie_name = f"{course.token}_last_viewed_unit_id"
        response.set_cookie(cookie_name,
                            str(current_unit_node.id),
                            samesite='Lax')
    except Exception:
        logger.error("Could not create cookie to save user's last_viewed_unit")

    if current_unit_node:
        logger.debug(f"Viewing page: {current_unit_node.display_name}")

    return response


@login_required
def course_search_page(request, course_slug, course_run):
    """
    Return search results from within current course.

    Args:
        request:
        course_slug:
        course_run:

    Returns:
        Response object
    """

    # TODO: Refactor to use AccessService

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    page_num = request.GET.get('page', 1)

    enrollment = get_object_or_404(Enrollment, student=request.user, course=course, active=True)
    if not can_access_course(user=request.user, course=course, enrollment=enrollment):
        return access_denied_page(request=request, course_slug=course.slug, course_run=course.run)
    if enrollment.enrollment_survey_required:
        enrollment_survey_url = reverse('catalog:enrollment_survey', kwargs={'course_slug': course.slug,
                                                                             'course_run': course.run})
        return redirect(enrollment_survey_url)

    search_text = request.GET.get('search_text', None)

    if len(search_text) > 100:
        search_text = search_text[:100]

    # We'll only be searching blocks in this particular course...
    course_blocks = Block.objects.filter(units__course=course)

    # Hits in the title (display_name) are worth more...
    search_vector = SearchVector('search_vector', weight='A')

    # Do a search against our vector fields
    search_query = SearchQuery(search_text)
    qs = course_blocks.filter(search_vector=search_query)
    qs = qs.annotate(rank=SearchRank(search_vector, search_query)).order_by('-rank')
    num_results = qs.count()

    paginator = Paginator(qs, 10)
    page_obj = paginator.page(page_num)
    current_blocks = page_obj.object_list
    block_ids = current_blocks.values_list('id', flat=True)

    headline_results = []
    for block_id in block_ids:
        block_query = Block.objects.filter(pk=block_id)
        block_query = block_query.annotate(all_content=Concat('html_content',
                                                              'json_content__header',
                                                              output_field=TextField()))
        block_query = block_query.annotate(
            headline=SearchHeadline(
                'all_content',
                search_query,
                start_sel='<mark>',
                stop_sel='</mark>'
            )
        )
        block: Block = block_query.get()
        headline_results.append(block)

    context = {
        "search_text": search_text,
        "course": course,
        "current_course_tab": "search",
        "current_course_tab_name": "Search",
        "search_results": headline_results,
        "page_obj": page_obj,
        "num_results": num_results
    }

    # Spin off an event to capture this activity
    Tracker.track(event_type=TrackingEventType.COURSE_SEARCH_REQUEST.value,
                  user=request.user,
                  event_data={
                      'search_text': search_text
                  },
                  course=course)

    return render(request, "course/course_search.html", context)


@login_required
def course_extra_page(request, course_slug, course_run, page_name):
    """
    This method just shows a generic html page for a course, with no interactive template functionality required.

    Args:
        request:
        course_slug:
        course_run:
        page_name:

    Returns:
        Response object
    """

    # TODO: Refactor to use AccessService

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course, active=True)
    if not can_access_course(user=request.user, course=course, enrollment=enrollment):
        return access_denied_page(request=request, course_slug=course.slug, course_run=course.run)
    if enrollment.enrollment_survey_required:
        enrollment_survey_url = reverse('catalog:enrollment_survey', kwargs={'course_slug': course.slug,
                                                                             'course_run': course.run})
        return redirect(enrollment_survey_url)

    template_name = 'course/custom/{}/{}/static_pages/{}.html'.format(course_slug, course_run, page_name)

    Tracker.track(event_type=TrackingEventType.COURSE_EXTRA_PAGE_VIEW.value,
                  user=request.user,
                  event_data={"page_name": page_name},
                  course=course,
                  unit_node_slug=None,
                  course_unit_id=None,
                  course_unit_slug=None,
                  block_uuid=None)

    context = {
        "course": course,
        "current_course_tab": page_name,
        "current_course_tab_name": page_name,
    }
    return render(request, template_name, context)


@ensure_csrf_cookie
@login_required
def certificate_download(request, course_slug, course_run):
    assert course_slug is not None
    assert course_run is not None

    # TODO: Refactor to use AccessService

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course, active=True)
    if not can_access_course(user=request.user, course=course, enrollment=enrollment):
        return access_denied_page(request=request, course_slug=course.slug, course_run=course.run)
    if enrollment.enrollment_survey_required:
        enrollment_survey_url = reverse('catalog:enrollment_survey',
                                        kwargs={'course_slug': course.slug,
                                                'course_run': course.run})
        return redirect(enrollment_survey_url)

    certificate_template, created = CertificateTemplateFactory.get_or_create_certificate_template(course=course)

    try:
        certificate = Certificate.objects.get(student=request.user, certificate_template=certificate_template)
    except Certificate.DoesNotExist:
        certificate = None

    # Generate PDF in buffer...
    if certificate_template.custom_template_name:
        cert_buffer = generate_custom_certificate(certificate)
    else:
        cert_buffer = generate_base_certificate(certificate)
    # Need to reset buffer to start before sending for download to work.
    cert_buffer.seek(0)

    certificate_filename = f"{certificate.student.username}_{course.token}_certificate.pdf"

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f"attachment; filename={certificate_filename}"
    response.write(cert_buffer.getvalue())
    cert_buffer.close()

    return response


@ensure_csrf_cookie
@login_required
def certificate_page(request, course_slug, course_run):
    # TODO: Refactor to use AccessService

    assert course_slug is not None
    assert course_run is not None

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course, active=True)
    if not can_access_course(user=request.user, course=course, enrollment=enrollment):
        return access_denied_page(request=request, course_slug=course.slug, course_run=course.run)
    if enrollment.enrollment_survey_required:
        enrollment_survey_url = reverse('catalog:enrollment_survey', kwargs={'course_slug': course.slug,
                                                                             'course_run': course.run})
        return redirect(enrollment_survey_url)

    context = {
        "course": course,
        "current_course_tab": "certificate",
        "current_course_tab_name": "Certificate"
    }
    try:
        certificate_template, created = CertificateTemplateFactory.get_or_create_certificate_template(course=course)
    except CertificateTemplate.DoesNotExist:
        logger.warning(f"No CertificateTemplate is defined for course {course}")
        return render(request, "course/certificate/no_certificate_template_defined_for_course.html", context)

    try:
        certificate = Certificate.objects.get(student=request.user, certificate_template=certificate_template)
    except Certificate.DoesNotExist:
        certificate = None

    if certificate:
        if certificate_template.custom_template_name:
            custom_certificate_template = f"course/certificate/custom/{certificate_template.custom_template_name}"
        else:
            custom_certificate_template = None
        signatories = certificate_template.signatories.all()
    else:
        signatories = []
        custom_certificate_template = None

    extra_context = {
        "certificate": certificate,
        "signatories": signatories,
        "custom_certificate_template": custom_certificate_template,
    }
    context.update(extra_context)

    Tracker.track(event_type=TrackingEventType.COURSE_CERTIFICATE_VIEW.value,
                  user=request.user,
                  event_data={'page': "certificate"},
                  course=course,
                  unit_node_slug=None,
                  course_unit_id=None,
                  course_unit_slug=None,
                  block_uuid=None)

    return render(request, "course/certificate/certificate_view.html", context)


@login_required
def forum_topics_page(request, course_slug=None, course_run=None):
    """
    Lists all forum topics in course on one tab.
    Disables those that haven't been released yet.

    Args:
        request:
        course_slug:
        course_run:

    Returns:
        Response object
    """

    # TODO: Refactor to use AccessService

    assert course_slug is not None
    assert course_run is not None
    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course, active=True)
    if not can_access_course(user=request.user, course=course, enrollment=enrollment):
        return access_denied_page(request=request, course_slug=course.slug, course_run=course.run)
    if enrollment.enrollment_survey_required:
        enrollment_survey_url = reverse('catalog:enrollment_survey', kwargs={'course_slug': course.slug,
                                                                             'course_run': course.run})
        return redirect(enrollment_survey_url)

    forum_topics_list: List[Dict] = []
    cohort = get_student_cohort(course=course, student=request.user)
    if cohort:
        # Find all "Discussion" blocks in the course and
        # remember the release state of each block.
        is_released_status = {}
        course_units = CourseUnit.objects.filter(course=course)
        order = {}
        index = 0
        for course_unit in course_units:
            blocks = course_unit.contents
            discussion_blocks = blocks.filter(type=BlockType.FORUM_TOPIC.name)
            for discussion_block in discussion_blocks:
                is_released_status[discussion_block.id] = course_unit.is_released
                order[discussion_block.id] = index
                index += 1
        try:
            forum_category = ForumCategory.objects.get(course=course)
            forum_subcategory = ForumSubcategory.objects.get(forum_category=forum_category,
                                                             type=ForumSubcategoryType.COHORT.name,
                                                             cohort_forum_group=cohort.cohort_forum_group)
            forum_topics = forum_subcategory.forum_topics.all()

            for forum_topic in forum_topics:
                try:
                    is_released = is_released_status[forum_topic.block.id]
                except Exception:
                    logger.exception(f"Could not get release status "
                                     f"for discussion_topic: {forum_topic}")
                    is_released = True

                try:
                    block_order = order[forum_topic.block.id]
                except Exception:
                    logger.exception(f"Could not get order for "
                                     f"discussion_topic: {forum_topic}")
                    block_order = 0

                form_provider = get_forum_provider()
                base_url = form_provider.forum_url

                forum_topic_dict = {
                    "url": f"{base_url}t/{forum_topic.topic_id}",
                    "title": forum_topic.title,
                    "is_released": is_released,
                    "order": block_order
                }
                forum_topics_list.append(forum_topic_dict)
        except Exception:
            logger.exception(f"Could not get forum topics for student {request.user}")
    else:
        logger.error(f"Could not find cohort for student {request.user}")

    forum_topics_list = sorted(forum_topics_list, key=lambda i: i['order'])
    context = {
        "course": course,
        "forum_topics": forum_topics_list,
        "current_course_tab": "forum_topics",
        "current_course_tab_name": "Forum Topics"
    }

    Tracker.track(event_type=TrackingEventType.COURSE_FORUM_TOPICS_VIEW.value,
                  user=request.user,
                  event_data={'page': "forum_topics"},
                  course=course,
                  unit_node_slug=None,
                  course_unit_id=None,
                  course_unit_slug=None,
                  block_uuid=None)

    return render(request, "course/forum_topics.html", context)


@login_required
def bookmarks_page(request, course_slug=None, course_run=None):
    # TODO: Refactor to use AccessService

    assert course_slug is not None
    assert course_run is not None

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course, active=True)
    if not can_access_course(user=request.user, course=course, enrollment=enrollment):
        return access_denied_page(request=request, course_slug=course.slug, course_run=course.run)
    if enrollment.enrollment_survey_required:
        enrollment_survey_url = reverse('catalog:enrollment_survey', kwargs={'course_slug': course.slug,
                                                                             'course_run': course.run})
        return redirect(enrollment_survey_url)

    bookmarks = Bookmark.objects.filter(course=course, student=request.user)

    context = {
        "current_course_tab": "bookmarks",
        "current_course_tab_name": "Bookmarks",
        "course": course,
        "bookmarks": bookmarks
    }

    Tracker.track(event_type=TrackingEventType.COURSE_BOOKMARKS_VIEW.value,
                  user=request.user,
                  event_data={'page': "bookmarks"},
                  course=course,
                  unit_node_slug=None,
                  course_unit_id=None,
                  course_unit_slug=None,
                  block_uuid=None)

    return render(request, "course/bookmarks.html", context)


@login_required
def progress_redirect_view(request, course_slug=None, course_run=None):
    """
    Redirect to 'overview' when user hits top level /progress url.
    """
    url = reverse('course:progress_overview_page',
                  kwargs={"course_slug": course_slug,
                          "course_run": course_run})
    return redirect(url)


# noinspection PyUnresolvedReferences
@login_required
def progress_overview_page(request, course_slug=None, course_run=None):
    # TODO: Refactor to use AccessService

    assert course_slug is not None
    assert course_run is not None

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course, active=True)
    if not can_access_course(user=request.user, course=course, enrollment=enrollment):
        return access_denied_page(request=request, course_slug=course.slug, course_run=course.run)
    if enrollment.enrollment_survey_required:
        enrollment_survey_url = reverse('catalog:enrollment_survey', kwargs={'course_slug': course.slug,
                                                                             'course_run': course.run})
        return redirect(enrollment_survey_url)

    return_to_content_url = request.META.get('HTTP_REFERER', '/')
    if not return_to_content_url:
        return_to_content_url = get_first_course_page_url(course=course)

    milestones: List[Milestone] = course.milestones.all()
    required_milestone_data = []
    non_required_milestone_data = []

    # Don't show badge fields in non-required milestone
    # table if none of them have a badge associated.
    show_non_required_badge_fields = False
    for milestone in milestones:
        progress: MilestoneProgress = MilestoneProgress.objects.filter(
            course=course,
            milestone=milestone,
            student=request.user
        ).first()

        m = {
            "name": milestone.name,
            "description": milestone.description,
            "required_to_pass": milestone.required_to_pass,
            "created_at": milestone.created_at,
            "count_requirement": milestone.count_requirement,
            "min_score_requirement": milestone.min_score_requirement,
            "progress": progress
        }
        if milestone.required_to_pass:
            required_milestone_data.append(m)
        else:
            non_required_milestone_data.append(m)

    try:
        course_passed = CoursePassed.objects.get(student=request.user, course=course)
    except CoursePassed.DoesNotExist:
        course_passed = None

    try:
        certificate = Certificate.objects.get(student=request.user, certificate_template__course=course)
        certificate_url = certificate.certificate_url
    except Certificate.DoesNotExist:
        certificate_url = None

    # get a course passed badge class, if any
    try:
        course_passed_badge_class = BadgeClass.objects.get(course=course, type=BadgeClassType.COURSE_PASSED.name)
    except BadgeClass.DoesNotExist:
        course_passed_badge_class = None

    badge_assertion = None
    if course_passed_badge_class:
        try:
            badge_assertion = BadgeAssertion.objects.get(recipient=request.user,
                                                         badge_class=course_passed_badge_class)
        except BadgeAssertion.DoesNotExist:
            pass

    Tracker.track(event_type=TrackingEventType.COURSE_PROGRESS_VIEW.value,
                  user=request.user,
                  event_data={'page': "progress"},
                  course=course,
                  unit_node_slug=None,
                  course_unit_id=None,
                  course_unit_slug=None,
                  block_uuid=None)

    user_badges_enabled = request.user.get_settings().enable_badges

    context = {
        "course": course,
        "current_course_tab": "progress",
        "current_course_tab_name": "Progress",
        "return_to_content_url": return_to_content_url,
        "course_name": course.display_name,
        "required_milestones": required_milestone_data,
        "non_required_milestones": non_required_milestone_data,
        "show_non_required_badge_fields": show_non_required_badge_fields,
        "course_passed": course_passed,
        "certificate_url": certificate_url,
        "current_course_progress_tab": "course_progress_overview",
        # Badge info...
        "user_badges_enabled": user_badges_enabled,
        "course_awards_certificates": course.enable_certificates,
        "course_awards_badges": course.enable_badges,
        "course_passed_badge_class": course_passed_badge_class,
        "badge_assertion": badge_assertion
    }

    return render(request, "course/progress/progress_overview.html", context)


@login_required
def progress_detail_page(request, course_slug=None, course_run=None, module_id: int = None):
    # TODO: Refactor to use AccessService

    assert course_slug is not None
    assert course_run is not None

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course, active=True)
    if not can_access_course(user=request.user, course=course, enrollment=enrollment):
        return access_denied_page(request=request, course_slug=course.slug, course_run=course.run)
    if enrollment.enrollment_survey_required:
        enrollment_survey_url = reverse('catalog:enrollment_survey', kwargs={'course_slug': course.slug,
                                                                             'course_run': course.run})
        return redirect(enrollment_survey_url)

    if module_id:
        current_module_node = get_object_or_404(CourseNode, id=module_id)
        progress_status = get_progress_status(course=course,
                                              student=request.user,
                                              target_module_node=current_module_node)
    else:
        current_module_node = None
        progress_status = None

    course_nav = get_course_nav(course=course)

    context = {
        "course": course,
        "course_nav": course_nav,
        "current_module_node_id": module_id,
        "current_module_node": current_module_node,
        "progress_status": progress_status,
        "current_course_tab": "progress",
        "current_course_tab_name": "Progress",
        "current_course_progress_tab": "course_progress_detail"
    }

    return render(request, "course/progress/progress_detail.html", context)


@login_required
@ensure_csrf_cookie
def custom_app_page(request, course_slug=None, course_run=None, custom_app_slug=None):
    # TODO: Refactor to use AccessService

    assert course_slug is not None
    assert course_run is not None
    assert custom_app_slug is not None

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course, active=True)
    if not can_access_course(user=request.user, course=course, enrollment=enrollment):
        return access_denied_page(request=request, course_slug=course.slug, course_run=course.run)
    if enrollment.enrollment_survey_required:
        enrollment_survey_url = reverse('catalog:enrollment_survey', kwargs={'course_slug': course.slug,
                                                                             'course_run': course.run})
        return redirect(enrollment_survey_url)

    custom_app = get_object_or_404(CustomApp, course=course, slug=custom_app_slug)

    if custom_app.type == CustomAppTypes.COURSE_SPEAKERS.name:
        response = course_speakers(request, course=course, custom_app=custom_app)
    elif custom_app.type == CustomAppTypes.PEER_REVIEW_JOURNAL.name:
        response = peer_review_journal(request, course=course, custom_app=custom_app)
    elif custom_app.type == CustomAppTypes.SIMPLE_HTML_CONTENT.name:
        response = simple_html_content(request, course=course, custom_app=custom_app)
    else:
        logger.error("Unsupported custom app type {}".format(custom_app.type))
        raise Http404

    Tracker.track(event_type=TrackingEventType.COURSE_CUSTOM_APP_PAGE_VIEW.value,
                  user=request.user,
                  event_data={
                      'custom_app': custom_app.display_name
                  },
                  course=course,
                  unit_node_slug=None,
                  course_unit_id=None,
                  course_unit_slug=None,
                  block_uuid=None)

    return response


@login_required
def shortcut_to_unit(request, course_slug: str, course_run: str, unit_block_slug: str):
    """
    Find the first unit with given slug and redirect to it.
    NOTE: slugs aren't unique so might be more than one. We redirect to first.
    """

    # TODO: Refactor to use AccessService

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    if request.user.is_staff:
        pass
    else:
        # Only allow students to use shortcut if they're enrolled
        is_enrolled = user_is_enrolled(user=request.user, course=course)
        if not is_enrolled:
            return Http404()

    course_unit = CourseUnit.objects.filter(course=course, unit__slug=unit_block_slug).first()
    if not course_unit:
        return Http404()
    unit_node = course_unit.unit
    section_node = unit_node.parent
    module_node = section_node.parent

    unit_page_url = resolve_url('course:unit_page',
                                course_slug=course.slug,
                                course_run=course.run,
                                module_slug=module_node.slug,
                                section_slug=section_node.slug,
                                unit_slug=unit_node.slug)

    return redirect(unit_page_url)


@login_required
def shortcut_to_assessment(request,
                           course_slug: str,
                           course_run: str,
                           unit_block_slug: str):
    """
    Find the unit an assessment first appears in and return an
    HTTP redirect response to that unit.

    The convention here is to give a particular slug format to the UnitBlock that ties in a
    Block with an assessment.

    Args:
        request:
        course_slug:
        course_run:
        unit_block_slug:

    Returns:
        Redirect response for URL of unit assessment appears in.

    """

    # TODO: Refactor to use AccessService

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    if request.user.is_staff:
        pass
    else:
        # Only allow students to use shortcut if they're enrolled
        is_enrolled = user_is_enrolled(user=request.user, course=course)
        if not is_enrolled:
            return Http404()

    unit_block = get_object_or_404(UnitBlock, slug=unit_block_slug)
    if not unit_block_slug:
        return Http404()

    course_unit: CourseUnit = unit_block.course_unit
    unit_url = course_unit.get_url(course=course)
    if not unit_url:
        logger.exception(f"Could not find short for course_slug:{course_slug} "
                         f"course_run:{course_run} "
                         f"unit_block_slug:{unit_block_slug}")
        return Http404()
    assessment_slug = unit_block.block.assessment.slug
    redirect_url = f"{unit_url}#assessment_{assessment_slug}"
    return redirect(redirect_url)


@login_required
def download_course_resource(request,
                             course_slug: str,
                             course_run: str,
                             course_resource_id: int,):
    """
    Download a course resource.

    Args:
        request:
        course_slug:
        course_run:
        course_resource_id:

    Returns:
        request with download file
    """

    # TODO: Refactor to use AccessService

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    if request.user.is_staff:
        # always allow download
        pass
    else:
        is_enrolled = user_is_enrolled(user=request.user, course=course)
        if not is_enrolled:
            return Http404()
    course_resource = get_object_or_404(CourseResource, id=course_resource_id)
    file = course_resource.resource_file

    try:
        event_data = {
            "course_resource_name": course_resource.resource_file.name,
        }
        Tracker.track(event_type=TrackingEventType.COURSE_RESOURCE_DOWNLOAD.value,
                      user=request.user,
                      event_data=event_data,
                      course=course,
                      unit_node_slug=None,
                      course_unit_id=None,
                      course_unit_slug=None)
    except Exception:
        logger.exception("Could not track course resource download")

    file_data = file.read()
    response = HttpResponse(file_data, content_type='application/text charset=utf-8')
    content_disposition = f'attachment; filename="{file.name}"'
    response['Content-Disposition'] = content_disposition

    return response


@login_required
def download_resource(request, course_slug: str, course_run: str, block_resource_id: int):
    """
    Download a block resource.

    Args:
        request:
        course_slug:
        course_run:
        block_resource_id:

    Returns:
        request with download file
    """

    # TODO: Refactor to use AccessService

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    if request.user.is_staff:
        # always allow download
        pass
    else:
        is_enrolled = user_is_enrolled(user=request.user, course=course)
        if not is_enrolled:
            return Http404()
    block_resource = get_object_or_404(BlockResource, id=block_resource_id)
    resource: Resource = block_resource.resource
    file = block_resource.resource.resource_file

    try:
        block: Block = block_resource.block
        event_data = {
            "resource_type": resource.type,
            "resource_name": resource.resource_file.name,
            "block_id": block.id,
            "block_slug": block.slug
        }
        if resource.type == ResourceType.VIDEO_TRANSCRIPT.name:
            event_data["video_id"] = block.json_content.get('video_id', None)

        Tracker.track(event_type=TrackingEventType.COURSE_BLOCK_RESOURCE_DOWNLOAD.value,
                      user=request.user,
                      event_data=event_data,
                      course=course,
                      block_uuid=block.uuid,
                      unit_node_slug=None,
                      course_unit_id=None,
                      course_unit_slug=None)
    except Exception:
        logger.exception("Could not track course resource download")

    file_data = file.read()
    response = HttpResponse(file_data, content_type='application/text charset=utf-8')
    content_disposition = f'attachment; filename="{file.name}"'
    response['Content-Disposition'] = content_disposition

    return response


@csrf_exempt
@login_required
def toggle_main_nav(request, *args, **kwargs):
    """
    Allows user to show/hide main nav and have setting persist.
    """

    try:
        json_data = json.loads(request.body)
        hide_main_nav: bool = json_data.get('hide_main_nav', False)
        request.session['hide_main_nav'] = hide_main_nav
    except Exception:
        logger.exception("Could not toggle main nav")   
    return HttpResponse()


@login_required
def outline_course(request, course_slug=None, course_run=None):
    """
    Displays entire course as one HTML page.

    Args:
        request:
        course_slug:
        course_run:

    Returns:
        response object
    """

    # TODO: Refactor to use AccessService

    course = get_object_or_404(Course, slug=course_slug, run=course_run)

    if course.enable_course_outline is False:
        raise Http404("Course outline is not available for this course")

    f = request.GET.get('filter', None)
    if f == 'assessments':
        template = 'course/outline/outline_course_assessments.html'
    else:
        template = 'course/outline/outline_course.html'

    module_nodes = course.course_root_node.get_descendants().prefetch_related()

    context = {
        "filter": f,
        "section": "management",
        "is_outline": True,
        "course": course,
        "module_nodes": module_nodes
    }

    return render(request, template, context)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# HTMX VIEW METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@login_required
def unit_summary_hx(request,
                    course_slug=None,
                    course_run=None,
                    module_slug=None,
                    section_slug=None,
                    unit_slug=None):
    # TODO: Refactor below to use process_course_hx_request() method

    if course_slug is None:
        raise ValueError('course_slug cannot be None')
    if course_run is None:
        raise ValueError('course_run cannot be None')
    if module_slug is None:
        raise ValueError('module_slug cannot be None')
    if section_slug is None:
        raise ValueError('section_slug cannot be None')
    if unit_slug is None:
        raise ValueError('unit_slug cannot be None')

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course, active=True)
    if not can_access_course(request.user, course, enrollment=enrollment):
        return access_denied_page(request=request, course_slug=course.slug, course_run=course.run)
    if enrollment.enrollment_survey_required:
        enrollment_survey_url = reverse('catalog:enrollment_survey', kwargs={'course_slug': course.slug,
                                                                             'course_run': course.run})
        return redirect(enrollment_survey_url)

    course_unit_url = None
    try:
        course_unit_url = reverse('course:unit_page',
                                  kwargs={'course_slug': course_slug,
                                          'course_run': course_run,
                                          'module_slug': module_slug,
                                          'section_slug': section_slug,
                                          'unit_slug': unit_slug})
    except Exception:
        logger.exception("Could not generate course unit url")

    is_beta_tester = enrollment.beta_tester
    # Get dictionary for nav
    try:
        course_nav: Dict = get_course_nav(course, is_beta_tester=is_beta_tester)
    except CourseNavException:
        logger.exception(f"unit_page():  Could not generate course {course} navigation with "
                         f"call to get_course_nav()")
        raise Exception("Internal error. Please contact support for help.")

    try:
        unit_nav_info: UnitNavInfo = get_unit_nav_info(course_nav,
                                                       module_node_slug=module_slug,
                                                       section_node_slug=section_slug,
                                                       unit_node_slug=unit_slug,
                                                       self_paced=course.self_paced)
    except ModuleNodeDoesNotExist:
        raise Http404("Module does not exist")
    except SectionNodeDoesNotExist:
        raise Http404("Section does not exist")
    except UnitNodeDoesNotExist:
        raise Http404("Unit does not exist")
    except ModuleNodeNotReleased as mnr:
        raise Http404(f"Module is not yet released. Release date: {mnr.node['release_datetime']}")
    except SectionNodeNotReleased as snr:
        raise Http404(f"Section is not yet released. Release date: {snr.node['release_datetime']}")
    except Exception:
        logger.exception("Could not build nav info")
        raise Http404("No unit found.")

    if course.self_paced:
        unit_is_released = True
        unit_release_datetime = None
    else:
        unit_is_released = unit_nav_info.unit_node_released
        unit_release_datetime = unit_nav_info.unit_node_release_datetime

    if unit_is_released:
        # Get CourseNode
        try:
            current_unit_node = CourseNode.objects.get(id=unit_nav_info.unit_node_id)
        except Exception:
            # Even though we have the ID of a 'UNIT' CourseNode ID in the cached nav...we don't have an
            # actual instance of this node with that ID in the database.
            logger.error(f"Could not find CourseNode with id {unit_nav_info.unit_node_id}")
            raise Http404("No unit found.")

        # Get CourseUnit
        try:
            course_unit: Optional[CourseUnit] = current_unit_node.unit
            if not course_unit:
                raise Exception("Missing unit")
        except Exception:
            raise Http404("Course is missing this unit.")
    else:
        course_unit = None

    context = {
        "course_unit": course_unit,
        "course_unit_url": course_unit_url,
        "unit_is_released": unit_is_released,
        "unit_nav_info": unit_nav_info,
        "unit_release_datetime": unit_release_datetime
    }
    return render(request, 'course/hx/unit_summary_hx.html', context)


@login_required
def toggle_bookmark_hx(request,
                       course_slug=None,
                       course_run=None,
                       module_slug=None,
                       section_slug=None,
                       unit_slug=None):
    """
    Toggle the selected bookmark on/off for the current unit.
    Track interaction.
    """

    # TODO: Refactor to use AccessService

    try:
        course, enrollment, course_nav, unit_nav_info = process_course_hx_request(
            request,
            course_slug=course_slug,
            course_run=course_run,
            module_slug=module_slug,
            section_slug=section_slug,
            unit_slug=unit_slug)
    except PermissionDenied:
        logger.exception("User does not have permission to call this htmx endpoint")
        return HttpResponseForbidden(_("You do not have permission to perform the requested action."))
    except Exception:
        logger.exception("Could not process course htmx request")
        raise Http404(_("Error processing your request"))

    try:
        bookmark, created = Bookmark.objects.get_or_create(student=request.user,
                                                           course=course,
                                                           unit_node_id=unit_nav_info.unit_node_id)
    except Exception:
        logger.exception("Could not create bookmark")
        raise Http404(_("Error processing your request"))

    if not created:
        # User is toggling bookmark off
        bookmark.delete()
        bookmark = None

    try:
        if bookmark:
            event_type = TrackingEventType.BOOKMARK_CREATED.value
        else:
            event_type = TrackingEventType.BOOKMARK_DELETED.value

        # Track this bookmark interaction...
        unit_node = bookmark.unit_node
        course_unit = unit_node.unit
        Tracker.track(event_type=event_type,
                      user=request.user,
                      event_data=None,
                      course=course,
                      unit_node_slug=unit_node.slug,
                      course_unit_id=course_unit.id,
                      course_unit_slug=course_unit.slug,
                      block_uuid=None)
    except Exception:
        logger.exception("Could not track bookmark interaction")
        # fail silently

    context = {
        "course": course,
        "bookmark": bookmark,
        "course_slug": course_slug,
        "course_run": course_run,
        "module_slug": module_slug,
        "section_slug": section_slug,
        "unit_slug": unit_slug,
        "current_unit_node_id": unit_nav_info.unit_node_id
    }
    return render(request, 'course/hx/bookmark_hx.html', context)


@login_required
def forum_topic_posts_hx(request,
                         course_slug=None,
                         course_run=None,
                         forum_topic_id: int = None):
    """
    Returns an HTML partial with the current posts for a forum topic.

    We don't really worry about whether the unit a forum topic appears in
    is released or not. (Students can view all forum topics for the course in the form tab.)

    """

    # TODO: Refactor to use AccessService

    course = None
    load_error = None
    topic = None
    topic_url = None
    posts = []

    # TODO: Make sure ForumTopic is accessible to student's cohort.

    try:
        course, enrollment, course_nav, unit_nav_info = process_course_hx_request(
            request,
            course_slug=course_slug,
            course_run=course_run)
        topic = get_object_or_404(ForumTopic, topic_id=forum_topic_id)
        service: BaseForumService = get_forum_service()
        if not service.user_can_view_topic(forum_topic=topic,
                                           user=request.user):
            raise PermissionDenied("User does not have permission to view this topic")
        topic_url = service.topic_url(forum_topic=topic)
        posts = service.get_topic_posts(forum_topic_id)
    except PermissionDenied:
        logger.exception("User does not have permission to call this htmx endpoint")
        load_error = _("You do not have permission to view these posts")
    except Exception:
        logger.exception("Could not process course htmx request")
        raise Http404(_("Error processing your request"))

    context = {
        "course": course,
        "topic": topic,
        "topic_url": topic_url,
        "load_error": load_error,
        "topic_posts": posts
    }

    return render(request, 'course/blocks/forum_topic/forum_topic_posts.html', context)
