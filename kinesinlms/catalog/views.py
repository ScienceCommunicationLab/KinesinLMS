import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.views.decorators.http import require_http_methods

from kinesinlms.assessments.utils import get_num_block_type_for_node
from kinesinlms.badges.models import BadgeClass
from kinesinlms.catalog.forms import EnrollmentSurveyAnswerForm
from kinesinlms.catalog.models import CourseCatalogDescription
from kinesinlms.catalog.service import (
    EnrollmentPeriodHasNotStarted,
    StudentAlreadyEnrolled,
    do_enrollment,
    do_unenrollment,
)
from kinesinlms.course.models import Course, Enrollment, EnrollmentSurveyCompletion, Milestone
from kinesinlms.course.utils import can_enroll, user_is_enrolled
from kinesinlms.course.utils_access import can_access_course
from kinesinlms.course.views import CourseNavException, get_course_nav
from kinesinlms.learning_library.constants import BlockType

logger = logging.getLogger(__name__)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# VIEW METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# PUBLIC VIEW METHODS
# ............................................


def index(request):
    """
    Shows a list of available courses.

    Get a list of course descriptions and add to context for
    the course catalog to render catalog cards.

    Args:
        request :       Request object

    Returns:
        A populated HttpResponse

    """

    if request.user.is_staff or request.user.is_superuser:
        course_descriptions = CourseCatalogDescription.objects.all()
    else:
        course_descriptions = CourseCatalogDescription.objects.filter(visible=True)

        try:
            # If user is enrolled, add invisible courses the student has enrolled in.
            if request.user.is_authenticated and hasattr(request.user, "enrollments"):
                try:
                    show_course_description_ids = [
                        enrollment.course.catalog_description.id for enrollment in request.user.enrollments.all()
                    ]
                    extra_course_descriptions = CourseCatalogDescription.objects.filter(
                        visible=False, id__in=show_course_description_ids
                    )
                    if extra_course_descriptions:
                        # you can concatenate querysets with |
                        course_descriptions = course_descriptions | extra_course_descriptions
                except Exception:
                    logger.exception("Could not hidden and enrolled courses to front page")
        except Exception:
            logger.exception("Could not add extra course descriptions to student's view in catalog")

    context = {
        "section": "catalog",
        "title": "Course Catalog",
        "description": "A list of all the courses we're offering or plan to offer.",
        "course_descriptions": course_descriptions,
    }

    return render(request, "catalog/index.html", context)


def about_page(request, course_slug: str = None, course_run: str = None):
    """
     Show about info page for a course and run.

    Args:
         request :       Request object.
         course_slug :   Course slug
         course_run :    Course run

     Returns:
         A populated HttpResponse

    """

    # The CourseCatalogDescription decides which courses are visible to the public.
    # So we'll use that to determine whether we show the page or a 404.
    course = get_object_or_404(Course, slug=course_slug, run=course_run)

    try:
        course_description = get_object_or_404(CourseCatalogDescription, course=course)
    except CourseCatalogDescription.DoesNotExist:
        logger.exception(f"Course {course} is missing a CourseCatalogDescription.")
        raise Http404()

    unenrollment_url = None
    enrollment_url = None
    course_url = None
    is_enrolled = False
    user_can_access_course = False
    is_beta_tester = False

    user_can_enroll = can_enroll(user=request.user, course=course)

    if request.user.is_authenticated:
        # See if user is enrolled before checking whether they can view this about page.
        is_enrolled = False
        try:
            enrollment = Enrollment.objects.get(student=request.user, course=course)
            is_enrolled = enrollment.active
            if enrollment.active:
                unenrollment_url = resolve_url("catalog:unenroll", course_slug=course.slug, course_run=course.run)
                course_url = resolve_url("course:course_page", course_slug=course.slug, course_run=course.run)
                user_can_access_course = can_access_course(user=request.user, course=course)
                is_beta_tester = enrollment.beta_tester
            else:
                enrollment_url = resolve_url("catalog:enroll", course_slug=course.slug, course_run=course.run)
        except Enrollment.DoesNotExist:
            enrollment_url = resolve_url("catalog:enroll", course_slug=course.slug, course_run=course.run)

        if not course_description.visible:
            # Only certain users can see a catalog about page marked visible = False
            if request.user.is_staff or request.user.is_superuser:
                logger.debug("Showing about page for hidden course to superuser or staff.")
            elif is_enrolled:
                logger.debug("Showing about page for hidden course to student enrolled in course.")
            else:
                raise Http404(f"No course about page found for course {course_slug}_{course_run}")

    else:
        if not course_description.visible:
            raise Http404(f"No course about page found for course {course_slug}_{course_run}")

    breadcrumbs = [{"url": "/catalog", "label": "Course Catalog"}]

    context = {
        "section": "catalog",
        "title": f"About Course {course.token}",
        "breadcrumbs": breadcrumbs,
        "course_description": course_description,
        "user_can_enroll": user_can_enroll,
        "user_can_access_course": user_can_access_course,
        "is_beta_tester": is_beta_tester,
        "is_enrolled": is_enrolled,
        "enrollment_url": enrollment_url,
        "unenrollment_url": unenrollment_url,
        "course": course,
        "course_url": course_url,
        "course_slug": course_slug,
        "course_run": course_run,
    }

    return render(request, "catalog/about_course.html", context)


def criteria_page(request, course_slug: str = None, course_run: str = None):
    """
    Show information about the criteria needed to pass a course.

    Args:
        request :       Request object.
        course_slug :   Course slug
        course_run :    Course run

    Returns:
        A populated HttpResponse
    """

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    # The CourseCatalogDescription decides which courses are visible to the public.
    # So we'll use that to determine whether we show the page or a 404.
    try:
        course_description = get_object_or_404(CourseCatalogDescription, course=course)
    except CourseCatalogDescription.DoesNotExist:
        logger.exception(f"Course {course} is missing a CourseCatalogDescription.")
        raise Http404()
    if not course_description.visible:
        logger.warning(f"Someone wants to see a course that's not visible right now. Course: {course}")
        raise Http404()

    try:
        badge_class = BadgeClass.objects.get(course=course)
    except BadgeClass.DoesNotExist:
        logger.warning(f"criteria page cannot find a BadgeClass instance for course: {course}")
        badge_class = None

    breadcrumbs = [
        {"url": "/catalog", "label": "Course Catalog"},
        {"url": f"/catalog/{course.slug}/{course.run}", "label": f"About {course.token}"},
    ]

    modules_info = []
    total_num_assessments = 0
    total_num_graded_assessments = 0
    total_num_sits = 0
    total_num_graded_sits = 0
    try:
        course_nav = get_course_nav(course)
        module_nodes = course_nav.get("children", [])
        for module_node in module_nodes:
            num_assessments = get_num_block_type_for_node(module_node, BlockType.ASSESSMENT, graded_only=False)
            num_graded_assessments = get_num_block_type_for_node(module_node, BlockType.ASSESSMENT, graded_only=True)

            num_sits = get_num_block_type_for_node(module_node, BlockType.SIMPLE_INTERACTIVE_TOOL, graded_only=False)
            num_graded_sits = get_num_block_type_for_node(
                module_node, BlockType.SIMPLE_INTERACTIVE_TOOL, graded_only=True
            )

            module_info = {
                "display_name": module_node.get("display_name", None),
                "number_of_assessments": num_assessments or "",
                "num_graded_assessments": num_graded_assessments or "",
                "number_of_sits": num_sits or "",
                "num_graded_sits": num_graded_sits or "",
            }
            total_num_assessments += num_assessments
            total_num_graded_assessments += num_graded_assessments
            total_num_sits += num_sits
            total_num_graded_sits += num_graded_sits
            modules_info.append(module_info)
    except CourseNavException:
        pass

    required_milestones = Milestone.objects.filter(course=course, required_to_pass=True)

    badge_image_filename = f"course_passed_badge_{course.slug}.svg"

    context = {
        "section": "catalog",
        "title": "Criteria for Passing",
        "modules_info": modules_info,
        "total_num_assessments": total_num_assessments,
        "total_num_graded_assessments": total_num_graded_assessments,
        "total_num_sits": total_num_sits,
        "total_num_graded_sits": total_num_graded_sits,
        "breadcrumbs": breadcrumbs,
        "badge_class": badge_class,
        "course_description": course_description,
        "required_milestones": required_milestones,
        "badge_image_filename": badge_image_filename,
    }

    return render(request, "catalog/about_course_criteria.html", context)


# VIEW METHODS FOR LOGGED IN USERS
# ............................................


@login_required
@require_http_methods(["GET", "POST"])
def enroll(request, course_slug=None, course_run=None):
    """
    Enroll the student in the course they've requested to be enrolled in, if they're allowed!
    (If they're not, return the request with a message saying why they can't enroll.)

    Args:
        request :       Request object
        course_slug :   Course slug
        course_run :    Course run

    Returns:
        A redirect to the about page, or an enrollment survey if one is defined.
        This method adds an enrollment success message to  Django messages, so
        the user will see that on the next page, and rest assured they have
        been enrolled.

    """

    if not course_slug:
        logger.exception("enroll(): Argument course_slug cannot be None. Returning 404...")
        raise Http404()
    if not course_run:
        logger.exception("enroll(): Argument cour   se_run cannot be None. Returning 404...")
        raise Http404()

    target_course = get_object_or_404(Course, slug=course_slug, run=course_run)

    if not request.user.is_superuser and not request.user.is_staff:
        if target_course.admin_only_enrollment:
            logger.error(f"Student {request.user} tried to enroll " f"in admin only enroll course: {target_course}")
            msg = "This course is not open for enrollment. You " "must be manually enrolled by the KinesinLMS staff."
            messages.add_message(request, messages.ERROR, msg)
            redirect("catalog:about_page", course_slug=target_course.slug, course_run=target_course.run)

    # OK TO TRY TO DO ENROLLMENT
    # Try to enroll user in course. The enroll button shouldn't have even been visible if they
    # were not allowed to enroll, so we should only be in this method if they're allowed to enroll.
    # However, we'll still check here for any other reasons an enrollment could be refused,
    # and report any back to the client.
    enrollment = None
    try:
        enrollment = do_enrollment(user=request.user, course=target_course)
        msg = "You have enrolled in this course."
        messages.add_message(request, messages.INFO, msg)
    except EnrollmentPeriodHasNotStarted:
        logger.error(
            f"enroll(): EnrollmentPeriodHasNotStarted: " f"Could not enroll {request.user} in course {target_course}."
        )
        msg = "The enrollment period for this course has not yet started."
        messages.add_message(request, messages.ERROR, msg)
    except StudentAlreadyEnrolled:
        logger.info(f"enroll(): StudentAlreadyEnrolled: Could not enroll " f"{request.user} in course {target_course}.")
        msg = "You are already enrolled in this course."
        messages.add_message(request, messages.ERROR, msg)
    except Exception:
        logger.exception(f"Couldn't enroll student {request.user} in course {target_course}.")
        msg = "Could not enroll in course. Please contact support for help."
        messages.add_message(request, messages.ERROR, msg)

    if enrollment and enrollment.enrollment_survey_required_url:
        return redirect(enrollment.enrollment_survey_required_url)
    else:
        return redirect("catalog:about_page", course_slug=target_course.slug, course_run=target_course.run)


@login_required
@require_http_methods(["GET", "POST"])
def enrollment_survey(request, course_slug=None, course_run=None):
    """
    Show the enrollment survey after the student has enrolled.
    """

    # Make sure user is enrolled (if not, send them back to about page).
    target_course = get_object_or_404(Course, slug=course_slug, run=course_run)
    e_survey = getattr(target_course, "enrollment_survey", None)
    if not user_is_enrolled(user=request.user, course=target_course) or e_survey is None:
        return redirect("catalog:about_page", course_slug=target_course.slug, course_run=target_course.run)

    try:
        enrollment = Enrollment.objects.get(student=request.user, course=target_course)
    except Enrollment.DoesNotExist:
        enrollment = None
    if enrollment and not enrollment.enrollment_survey_required_url:
        return redirect(
            "course:course_home_page",
            course_slug=target_course.slug,
            course_run=target_course.run,
        )

    if len(target_course.enrollment_survey.questions.all()) > 1:
        logger.warning("Only one enrollment question is supported at the moment")

    enrollment_question = target_course.enrollment_survey.questions.first()

    if request.method == "GET":
        enrollment_answer_form = EnrollmentSurveyAnswerForm(enrollment_question=enrollment_question)
        context = {
            "course": target_course,
            "enrollment_question": enrollment_question,
            "enrollment_answer_form": enrollment_answer_form,
        }
        return render(request, "catalog/enrollment_survey/enrollment_survey.html", context)

    elif request.method == "POST":
        enrollment_answer_form = EnrollmentSurveyAnswerForm(request.POST, enrollment_question=enrollment_question)
        if enrollment_answer_form.is_valid():
            enrollment_answer = enrollment_answer_form.save(commit=False)
            enrollment_answer.enrollment_question = enrollment_question
            enrollment_answer.enrollment = enrollment
            enrollment_answer.save()
            # We only handle one question at the moment.
            # So mark survey complete.
            # TODO: Create a way to handle multiple questions if necessary.
            EnrollmentSurveyCompletion.objects.get_or_create(
                enrollment_survey=target_course.enrollment_survey, student=request.user
            )
            logger.info(f"Student {request.user} answered enrollment survey : {enrollment_answer}")
            return redirect("catalog:about_page", course_slug=target_course.slug, course_run=target_course.run)
        else:
            context = {
                "course": target_course,
                "enrollment_question": enrollment_question,
                "enrollment_answer_form": enrollment_answer_form,
            }
            return render(request, "catalog/enrollment_survey/enrollment_survey.html", context)
    else:
        logger.exception(f"Unrecognized request method: {request.method}")
        return redirect("catalog:about_page", course_slug=target_course.slug, course_run=target_course.run)


@login_required
@require_http_methods(["POST"])
def unenroll(request, course_slug=None, course_run=None):
    """Unenroll the student in the course they've requested to be unenrolled from.

    Args:
        request :       Request object
        course_slug :   Course slug
        course_run :    Course run

    Returns:
        A redirect to the about page. This method adds an unenrollment success message to
        Django messages, so the user will see that on the about page, confirming
        their enrollment.
    """

    assert course_slug is not None
    assert course_run is not None

    student = request.user
    course = get_object_or_404(Course, slug=course_slug, run=course_run)

    try:
        do_unenrollment(user=student, course=course)
        msg = "You have unenrolled from this course."
        messages.add_message(request, messages.INFO, msg)
    except Enrollment.DoesNotExist:
        msg = "You are not enrolled in this course, so you cannot unenroll from it."
        messages.add_message(request, messages.INFO, msg)
        return redirect("catalog:about_page", course_slug=course.slug, course_run=course.run)
    except Exception:
        logger.exception(f"unenroll(): Error trying to unenroll student : {student} from" f"course {course} ")
        msg = (
            "There was an error when trying to unenroll you from this course. " "Please try again or support for help."
        )
        messages.add_message(request, messages.ERROR, msg)
        return redirect("catalog:about_page", course_slug=course.slug, course_run=course.run)

    return redirect("catalog:about_page", course_slug=course.slug, course_run=course.run)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# API VIEWS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# TODO: Add API endpoints if/when appropriate...
