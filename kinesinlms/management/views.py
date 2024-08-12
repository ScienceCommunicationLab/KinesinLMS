import logging

import django_filters
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.sites.models import Site
from django.shortcuts import render, get_object_or_404, resolve_url, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, UpdateView
from django_filters.views import FilterView

from waffle.models import Switch

from kinesinlms.certificates.models import Certificate
from kinesinlms.core.models import SiteProfile
from kinesinlms.course.models import Course, Enrollment
from kinesinlms.course.utils import get_student_cohort
from kinesinlms.forum.service.discourse_service import ForumAPIUnsuccessful
from kinesinlms.forum.utils import get_forum_service
from kinesinlms.learning_library.constants import AssessmentType, BlockType
from kinesinlms.learning_library.models import Block
from kinesinlms.management.forms import (
    ManualEnrollmentForm,
    ManualUnenrollmentForm,
    SiteFeaturesForm,
    SiteProfileForm,
)
from kinesinlms.management.models import ManualEnrollment, ManualUnenrollment

logger = logging.getLogger(__name__)

"""
The views in this module are for imports and exports courses in our own V2 format.
It has nothing to do with importing Open edX-based course archives. Open edX imports are done
via management command only (at the moment).

"""

User = get_user_model()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# VIEW CLASSES
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class StudentFilter(django_filters.FilterSet):
    username = django_filters.CharFilter(lookup_expr="icontains", label="Username")
    name = django_filters.CharFilter(lookup_expr="icontains", label="Name")
    email = django_filters.CharFilter(lookup_expr="icontains", label="Email")
    enrollments = django_filters.ModelChoiceFilter(
        field_name="enrollments__course", label="Enrolled In"
    )

    class Meta:
        model = User
        fields = ["username", "name", "email", "enrollments"]

    def __init__(self, *args, **kwargs):
        super(StudentFilter, self).__init__(*args, **kwargs)
        self.filters["enrollments"].queryset = Course.objects.all()


class StudentsListView(UserPassesTestMixin, FilterView):
    model = User
    template_name = "management/students/list.html"
    context_object_name = "students"
    filterset_class = StudentFilter
    ordering = ["username", "name"]
    paginate_by = 25
    raise_exception = True

    def get_queryset(self):
        queryset = super().get_queryset()
        self.filterset = self.filterset_class(self.request.GET, queryset=queryset)
        return self.filterset.qs.distinct()

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context["student_count"] = User.objects.filter(
            is_staff=False, is_superuser=False, is_active=True
        ).count()
        context["title"] = "Student List"
        context["fluid_info_bar"] = True
        context["total_count"] = self.filterset.queryset.count()
        context["breadcrumbs"] = [
            {"label": "Management", "url": reverse("management:index")},
            {"label": "Manage Students", "url": reverse("management:students_manage")},
        ]
        return context

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff


class ManualEnrollmentFormView(UserPassesTestMixin, FormView):
    template_name = "management/students/manual_enrollment.html"
    form_class = ManualEnrollmentForm
    raise_exception = True

    def get_success_url(self) -> str:
        manual_enrollment_id = self.kwargs["id"]
        return reverse(
            "management:students_manual_enrollment_success",
            kwargs={"pk": manual_enrollment_id},
        )

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        manual_enrollment: ManualEnrollment = form.create_enrollments(
            user=self.request.user
        )
        self.kwargs["id"] = manual_enrollment.id
        is_valid = super().form_valid(form)
        return is_valid

    def get_context_data(self, **kwargs):
        context = super(ManualEnrollmentFormView, self).get_context_data(**kwargs)
        extra_context = {
            "section": "management",
            "title": "Batch Enroll Students",
            "description": "Batch enroll one or more students in a course.",
            "fluid_info_bar": True,
            "breadcrumbs": [
                {"label": "Management", "url": reverse("management:index")},
                {
                    "label": "Manage Students",
                    "url": reverse("management:students_manage"),
                },
            ],
        }
        context = {**context, **extra_context}

        return context

    def test_func(self):
        logger.info("Running test_func...")
        passes_test = self.request.user.is_superuser or self.request.user.is_staff
        return passes_test


class ManualUnenrollmentFormView(UserPassesTestMixin, FormView):
    template_name = "management/students/manual_unenrollment.html"
    form_class = ManualUnenrollmentForm
    raise_exception = True

    def get_success_url(self):
        manual_unenrollment_id = self.kwargs["id"]
        return reverse(
            "management:students_manual_unenrollment_success",
            kwargs={"pk": manual_unenrollment_id},
        )

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        manual_unenrollment: ManualUnenrollment = form.do_unenrollments(
            user=self.request.user
        )
        self.kwargs["id"] = manual_unenrollment.id
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(ManualUnenrollmentFormView, self).get_context_data(**kwargs)
        extra_context = {
            "section": "management",
            "title": "Batch Unenroll Students",
            "description": "Batch unenroll one or more students in a course.",
            "fluid_info_bar": True,
            "breadcrumbs": [
                {"label": "Management", "url": reverse("management:index")},
                {
                    "label": "Manage Students",
                    "url": reverse("management:students_manage"),
                },
            ],
        }
        context = {**context, **extra_context}

        return context

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff


class SiteFeaturesView(FormView):
    model = SiteProfile
    form_class = SiteFeaturesForm
    template_name = "management/features/site_features_form.html"
    success_url = reverse_lazy("management:site_features")

    def form_valid(self, form):
        # Process the form data and save switches
        for switch_name, value in form.cleaned_data.items():
            switch = Switch.objects.get_or_create(name=switch_name)[0]
            switch.active = value
            switch.save()
        messages.success(self.request, "Site features updated.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        extra_context = {
            "breadcrumbs": [
                {"label": "Management", "url": reverse("management:index")}
            ],
            "section": "management",
            "title": "Site Features",
            "description": "Enable/disable features for the current site",
        }
        context.update(extra_context)
        return context


class SiteProfileUpdateView(UpdateView):
    model = SiteProfile
    form_class = SiteProfileForm
    template_name = "management/site/site_profile_form.html"
    context_object_name = "site_profile"

    def test_func(self):
        return self.request.user.is_superuser

    def get_object(self, queryset=...):
        site = Site.objects.get_current()
        site_profile = SiteProfile.objects.get_or_create(site=site)[0]
        return site_profile

    def get_success_url(self):
        success_url = reverse_lazy("management:site_profile")
        return success_url

    def form_valid(self, form):
        messages.success(self.request, "Site profile update successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        extra_context = {
            "breadcrumbs": [
                {"label": "Management", "url": reverse("management:index")}
            ],
            "section": "management",
            "title": "Site Profile",
            "description": "Settings for the current site",
        }
        context.update(extra_context)
        return context


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# VIEW METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def index(request):
    site = Site.objects.get_current()

    forum_provider_enabled = (
        hasattr(site, "forum_provider") and site.forum_provider.active
    )

    context = {
        "section": "management",
        "title": "Management",
        "description": "Info and functions for staff and super users.",
        "fluid_info_bar": True,
        "forum_provider_enabled": forum_provider_enabled and site.forum_provider.active,
    }

    return render(request, "management/index.html", context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def student_certificate(request, user_id: int, certificate_id: int):
    """
    Render a student's certificate for admin viewing. Use a custom certificate
    layout and info if defined via the CertificateTemplate model.
    """

    certificate = get_object_or_404(Certificate, id=certificate_id, student_id=user_id)
    course = certificate.certificate_template.course

    if certificate.certificate_template.custom_template_name:
        custom_certificate_template = f"course/certificate/custom/{certificate.certificate_template.custom_template_name}"
    else:
        custom_certificate_template = None

    context = {
        "certificate": certificate,
        "course": course,
        "signatories": certificate.certificate_template.signatories.all(),
        "custom_certificate_template": custom_certificate_template,
    }

    return render(request, "management/students/student_certificate.html", context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def students_manual_enrollment_success(request, pk: int):
    manual_enrollment = get_object_or_404(ManualEnrollment, id=pk)

    if manual_enrollment.added_student_ids:
        enrolled_students = User.objects.filter(
            id__in=manual_enrollment.added_student_ids
        )
    else:
        enrolled_students = []

    if manual_enrollment.added_student_ids:
        moved_students = User.objects.filter(
            id__in=manual_enrollment.moved_from_cohort_ids
        )
    else:
        moved_students = []

    if manual_enrollment.skipped_student_ids:
        skipped_students = User.objects.filter(
            id__in=manual_enrollment.skipped_student_ids
        )
    else:
        skipped_students = []

    form_errors = []
    if manual_enrollment.errors:
        form_errors = list(manual_enrollment.errors)

    context = {
        "filter": filter,
        "section": "management",
        "title": "Enroll Students",
        "description": "Manually enroll one or more students in a course.",
        "fluid_info_bar": True,
        "breadcrumbs": [
            {"label": "Management", "url": reverse("management:index")},
            {"label": "Students", "url": reverse("management:students_manage")},
            {
                "label": "Batch Enroll",
                "url": reverse("management:students_manual_enrollment"),
            },
        ],
        "manual_enrollment": manual_enrollment,
        "course": manual_enrollment.course,
        "enrolled_students": enrolled_students,
        "skipped_students": skipped_students,
        "moved_students": moved_students,
        "form_errors": form_errors,
    }
    template = "management/students/manual_enrollment_success.html"

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def students_manual_unenrollment_success(request, pk: int):
    manual_unenrollment = get_object_or_404(ManualUnenrollment, id=pk)

    if manual_unenrollment.unenrolled_student_ids:
        unenrolled_students = User.objects.filter(
            id__in=manual_unenrollment.unenrolled_student_ids
        )
    else:
        unenrolled_students = []

    if manual_unenrollment.skipped_student_ids:
        skipped_students = User.objects.filter(
            id__in=manual_unenrollment.skipped_student_ids
        )
    else:
        skipped_students = []

    form_errors = []
    if manual_unenrollment.errors:
        form_errors = list(manual_unenrollment.errors)

    context = {
        "filter": filter,
        "section": "management",
        "title": "Enroll Students",
        "description": "Manually unenroll one or more students in a course.",
        "fluid_info_bar": True,
        "breadcrumbs": [
            {"label": "Management", "url": reverse("management:index")},
            {"label": "Students", "url": reverse("management:students_manage")},
        ],
        "unenrolled_students": unenrolled_students,
        "skipped_students": skipped_students,
        "form_errors": form_errors,
    }
    template = "management/students/manual_unenrollment_success.html"

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def students_management(request):
    courses = Course.objects.all()
    context = {
        "section": "management",
        "title": "Manage Students",
        "description": "",
        "courses": courses,
        "fluid_info_bar": True,
        "student_count": User.objects.filter(
            is_staff=False, is_superuser=False, is_active=True
        ).count(),
        "breadcrumbs": [
            {"label": "Management", "url": reverse("management:index")},
        ],
    }
    return render(request, "management/students/management.html", context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def evaluations_page(request, course_slug=None, course_run=None):
    """
    This is a custom view made to retrieve evaluation questions.
    It just looks for any unit with a slug 'evaluation_questions'
    in the current course and writes out the answers.
    """
    assert course_slug is not None
    assert course_run is not None

    course = get_object_or_404(Course, slug=course_slug, run=course_run)

    # TODO: Restrict certain staff to certain courses

    evaluation_answers = get_assessment_answers(course=course)

    download_csv_url = reverse(
        "management:evaluations_download",
        kwargs={"course_slug": course_slug, "course_run": course_run},
    )
    context = {
        "evaluation_answers": evaluation_answers,
        "download_csv_url": download_csv_url,
    }

    return render(request, "management/evaluations.html", context)


# noinspection PyUnresolvedReferences
@user_passes_test(lambda u: u.is_superuser)
def sync_student_to_discourse(request, user_id: int):
    """
    Manually sync a student to Discourse. This includes
    making sure the SSO user exists and the student is in
    the current list of groups for the courses they're enrolled in.

    Args:
        request:
        user_id:

    Returns:
        HTTP response
    """

    # Skip if we're running tests and no Discourse info is defined
    if settings.TEST_RUN and not settings.DISCOURSE_API_KEY:
        logger.info(
            "Skipping sync_student_to_discourse() because we're "
            "running tests and no Discourse info defined."
        )
        return

    assert user_id is not None
    student = get_object_or_404(User, id=user_id)
    courses_list_url = resolve_url("management:students_list")

    forum_service = get_forum_service()

    # SYNC USER
    # First make sure user exists in Discourse...
    try:
        forum_service.sync_discourse_sso_user(user=student)
    except ForumAPIUnsuccessful:
        error_message = "Could not sync discourse SSO user"
        logger.exception(error_message)
        messages.add_message(request, messages.ERROR, error_message)
        return redirect(courses_list_url)

    msg = f"Synced student {student.username} to Discourse "
    messages.add_message(request, messages.INFO, msg)

    # ADD TO GROUPS
    # Then add user to each set of groups for each course user is enrolled in.
    enrollments = Enrollment.objects.filter(student=student, active=True).all()
    for enrollment in enrollments:
        course = enrollment.course
        try:
            add_user_to_discourse_groups_for_course(user=student, course=course)
        except Exception:
            error_message = (
                f"Could not add student {student} to Discourse course "
                f"group for course {course}. "
            )
            logger.error(error_message)
            messages.add_message(request, messages.ERROR, msg)

    return redirect(courses_list_url)


@user_passes_test(lambda u: u.is_superuser)
def add_student_to_discourse_groups_for_course(
    request, course_slug: str, course_run: str, user_id: int
):
    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    student = get_object_or_404(User, id=user_id)

    courses_list_url = resolve_url(
        "management:students_in_course_list",
        course_run=course_run,
        course_slug=course_slug,
    )

    # SYNC USER
    # First make sure user exists in Discourse...
    try:
        service = get_forum_service()
        service.sync_forum_sso_user(user=student)
    except ForumAPIUnsuccessful:
        error_message = "Could not sync discourse SSO user"
        logger.exception(error_message)
        messages.add_message(request, messages.ERROR, error_message)
        return redirect(courses_list_url)

    msg = f"Synced student {student.username} to Discourse "
    messages.add_message(request, messages.INFO, msg)

    # ADD TO GROUPS
    # Then add student to Discourse groups for selected course
    error_msg = None
    try:
        enrollment = Enrollment.objects.get(course=course, student=student)
        if not enrollment.active:
            error_msg = f"Student {student} is not actively enrolled in course {course}"
            messages.add_message(request, messages.ERROR, error_msg)
    except Enrollment.DoesNotExist:
        error_msg = f"Student {student} is not enrolled in course {course}"
        messages.add_message(request, messages.ERROR, error_msg)
    except Exception:
        logger.exception("add_student_to_discourse_groups_for_course() exception")
        error_msg = (
            f"Error. Could not add student {student} to discourse "
            f"group for course {course}."
        )
        messages.add_message(request, messages.ERROR, error_msg)

    if error_msg:
        return redirect(courses_list_url)

    try:
        add_user_to_discourse_groups_for_course(user=student, course=course)
        msg = f"Add student {student.username} to Discourse groups for course {course} "
        messages.add_message(request, messages.INFO, msg)
    except Exception:
        error_message = (
            f"Could not add student {student} to Discourse course "
            f"group for course {course}."
        )
        logger.exception(error_message)
        messages.add_message(request, messages.ERROR, msg)

    return redirect(courses_list_url)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# HTMX METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def cohorts_select_hx(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)
    form = ManualEnrollmentForm(initial={"course": course})
    context = {"form": form}
    return render(request, "management/forms/manual_enrollment_form.html", context)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Admin controls
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def toggle_admin_controls(request, *args, **kwargs):
    show_controls = request.GET.get("show_admin_controls", False)
    if show_controls.upper() == "TRUE":
        show_controls = True
    else:
        show_controls = False
    request.session["show_admin_controls"] = show_controls
    referrer = request.META.get("HTTP_REFERER", None)
    if referrer:
        return redirect(request.META["HTTP_REFERER"])
    else:
        return redirect("/")


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# VIEW HELPER METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def add_user_to_discourse_groups_for_course(user, course: Course):
    """
    Adds a user to the appropriate Discourse groups for a particular course:
        - Discourse Course Group
        - Discourse Cohort Group

    Args:
        user:
        course:

    Raises:
        Exception on error or if no CohortForumGroup is defined for
        student's cohort.
    """

    # COURSE GROUP
    # Add to course group
    course_forum_group_id = course.course_forum_group.group_id
    username = user.username

    service = get_forum_service()
    service.add_user_to_group(group_id=course_forum_group_id, username=username)

    # COHORT GROUP
    # Add to cohort group
    cohort = get_student_cohort(course=course, student=user)
    if cohort.cohort_forum_group:
        discourse_group_id = cohort.cohort_forum_group.group_id
        service.add_user_to_group(group_id=discourse_group_id, username=username)
    else:
        raise Exception(
            f"Cannot add user to discourse groups for course {course} "
            f"as there is no CohortForumGroup for cohort {cohort}"
        )


def get_assessment_answers(course=None):
    assert course is not None
    assessment_answers = []
    eval_unit = Block.objects.get(
        type=BlockType.ASSESSMENT.name, slug="evaluation_questions"
    )
    for block in eval_unit.blocks:
        if (
            block.type == BlockType.ASSESSMENT.name
            and block.assessment.type == AssessmentType.LONG_FORM_TEXT.name
        ):
            for submitted_answer in block.assessment.answers:
                assessment_answers.append(
                    {
                        "user": submitted_answer.student.username,
                        "question": block.display_name,
                        "answer": submitted_answer.answer,
                    }
                )
    return assessment_answers
