import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models.query import QuerySet
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, DetailView

from kinesinlms.course.models import Course
from kinesinlms.course_enrollment.forms import ManualEnrollmentForm
from kinesinlms.management.models import ManualEnrollment
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.tracker import Tracker
from kinesinlms.tracking.models import TrackingEvent
from kinesinlms.users.models import InviteUser
from kinesinlms.users.filters import UserFilter


from kinesinlms.core.decorators import course_staff_required
from kinesinlms.core.mixins import EducatorCourseStaffMixin

logger = logging.getLogger(__name__)

User = get_user_model()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# VIEW CLASSES
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class EnrolledStudentsListView(EducatorCourseStaffMixin, ListView):
    """
    List enrolled students in a given course.
    """

    context_object_name = "enrolled_students"
    template_name = "course_admin/course_enrollment/enrolled_students_list.html"
    raise_exception = True

    def get_queryset(self) -> QuerySet[User]:
        course_run = self.kwargs.get("course_run")
        course_slug = self.kwargs.get("course_slug")
        if not course_run or not course_slug:
            return User.objects.none()

        enrolled_students_qs = User.objects.filter(
            enrollments__course__run=course_run,
            enrollments__course__slug=course_slug,
        )
        self.filter_set = UserFilter(self.request.GET, enrolled_students_qs)
        return self.filter_set.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_run = self.kwargs.get("course_run")
        course_slug = self.kwargs.get("course_slug")
        course = get_object_or_404(Course, run=course_run, slug=course_slug)
        course_admin_breadcrumbs = [
            {
                "label": "Course Enrollment",
                "url": reverse(
                    "course:course_admin:course_enrollment:index",
                    kwargs={
                        "course_run": self.kwargs.get("course_run"),
                        "course_slug": self.kwargs.get("course_slug"),
                    },
                ),
            },
            {"label": "Enrolled Students"},
        ]
        extra_context = {
            "course_admin_breadcrumbs": course_admin_breadcrumbs,
            "course_run": course_run,
            "course_slug": course_slug,
            "course": course,
            "search_form": self.filter_set.form,
            "current_course_tab": "course_admin",
            "current_course_tab_name": "Course Admin",
            "current_course_admin_tab": "course_enrollment",
            "course_admin_page_title": "Enrolled Students",
        }
        context.update(extra_context)
        return context


class EnrolledStudentDetailView(EducatorCourseStaffMixin, DetailView):
    """
    Show details for an enrolled student
    """

    context_object_name = "student"
    template_name = "course_admin/course_enrollment/enrolled_student_detail.html"
    queryset = User.objects.all()
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_run = self.kwargs.get("course_run")
        course_slug = self.kwargs.get("course_slug")
        course = get_object_or_404(Course, run=course_run, slug=course_slug)
        course_admin_breadcrumbs = [
            {
                "label": "Course Enrollment",
                "url": reverse(
                    "course:course_admin:course_enrollment:index",
                    kwargs={
                        "course_run": self.kwargs.get("course_run"),
                        "course_slug": self.kwargs.get("course_slug"),
                    },
                ),
            },
            {
                "label": "Enrolled Students",
                "url": reverse(
                    "course:course_admin:course_enrollment:enrolled_students_list",
                    kwargs={
                        "course_run": self.kwargs.get("course_run"),
                        "course_slug": self.kwargs.get("course_slug"),
                    },
                ),
            },
            {
                "label": f"User: {self.object.username}",
            },
        ]
        extra_context = {
            "course_admin_breadcrumbs": course_admin_breadcrumbs,
            "course_run": course_run,
            "course_slug": course_slug,
            "course": course,
            "current_course_tab": "course_admin",
            "current_course_tab_name": "Course Admin",
            "current_course_admin_tab": "course_enrollment",
            "course_admin_page_title": f"User: {self.object.username}",
        }
        context.update(extra_context)
        return context


class EnrolledStudentEventsListView(EducatorCourseStaffMixin, ListView):
    """
    List the events for a single student enrolled in this course.
    """

    model = TrackingEvent
    template_name = "course_admin/course_enrollment/enrolled_student_events.html"
    context_object_name = "events"

    def get_queryset(self):
        course_run = self.kwargs.get("course_run")
        course_slug = self.kwargs.get("course_slug")
        student_id = self.kwargs.get("pk")
        events = TrackingEvent.objects.filter(
            course_slug=course_slug, course_run=course_run, user=student_id
        )
        return events

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_run = self.kwargs.get("course_run")
        course_slug = self.kwargs.get("course_slug")
        course = get_object_or_404(Course, run=course_run, slug=course_slug)
        user = User.objects.get(id=self.kwargs.get("pk"))
        course_admin_breadcrumbs = [
            {
                "label": "Course Enrollment",
                "url": reverse(
                    "course:course_admin:course_enrollment:index",
                    kwargs={
                        "course_run": self.kwargs.get("course_run"),
                        "course_slug": self.kwargs.get("course_slug"),
                    },
                ),
            },
            {
                "label": "Enrolled Students",
                "url": reverse(
                    "course:course_admin:course_enrollment:enrolled_students_list",
                    kwargs={
                        "course_run": self.kwargs.get("course_run"),
                        "course_slug": self.kwargs.get("course_slug"),
                    },
                ),
            },
            {
                "label": f"User: {user.username}",
                "url": reverse(
                    "course:course_admin:course_enrollment:enrolled_student_detail_view",
                    kwargs={
                        "course_run": self.kwargs.get("course_run"),
                        "course_slug": self.kwargs.get("course_slug"),
                        "pk": user.id,
                    },
                ),
            },
            {"label": "Activity Events"},
        ]
        extra_context = {
            "course_admin_breadcrumbs": course_admin_breadcrumbs,
            "course_run": course_run,
            "course_slug": course_slug,
            "course": course,
            "current_course_tab": "course_admin",
            "current_course_tab_name": "Course Admin",
            "current_course_admin_tab": "course_enrollment",
            "course_admin_page_title": "Activity Events",
        }
        context.update(extra_context)
        return context


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# VIEW METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@course_staff_required
def index(request, course_run: str, course_slug: str):
    """
    Main view for Course Enrollment section in course.
    """

    course = get_object_or_404(Course, run=course_run, slug=course_slug)

    context = {
        "course": course,
        "course_slug": course_slug,
        "course_run": course_run,
        "current_course_tab": "course_admin",
        "current_course_tab_name": "Course Admin",
        "current_course_admin_tab": "course_enrollment",
        "course_admin_page_title": "Course Enrollment",
    }

    Tracker.track(
        event_type=TrackingEventType.COURSE_ADMIN_PAGE_VIEW.value,
        user=request.user,
        event_data={"course_admin_tab": "course_enrollment", "tab_page": "index"},
        course=course,
    )

    return render(request, "course_admin/course_enrollment/index.html", context)


@course_staff_required
def manual_enrollment(request, course_run: str, course_slug: str):
    """
    Main view for Course Enrollment section in course.
    """

    course = get_object_or_404(Course, run=course_run, slug=course_slug)

    course_admin_breadcrumbs = [
        {
            "label": "Course Enrollment",
            "url": reverse(
                "course:course_admin:course_enrollment:index",
                kwargs={"course_run": course.run, "course_slug": course.slug},
            ),
        },
        {"label": "Manual Enrollment"},
    ]

    context = {
        "course": course,
        "course_slug": course_slug,
        "course_run": course_run,
        "course_admin_breadcrumbs": course_admin_breadcrumbs,
        "current_course_tab": "course_admin",
        "current_course_tab_name": "Course Admin",
        "current_course_admin_tab": "course_enrollment",
        "course_admin_page_title": "Manually Enroll Students",
    }

    template_name = "course_admin/course_enrollment/manual_enrollment.html"
    if request.POST:
        form = ManualEnrollmentForm(request.POST)
        if form.is_valid():
            me: ManualEnrollment = form.save(user=request.user)
            template_name = (
                "course_admin/course_enrollment/manual_enrollment_success.html"
            )
            context["manual_enrollment"] = me

            if me.added_student_ids:
                enrolled_students = User.objects.filter(id__in=me.added_student_ids)
            else:
                enrolled_students = []

            if me.added_student_ids:
                moved_students = User.objects.filter(id__in=me.moved_from_cohort_ids)
            else:
                moved_students = []

            if me.skipped_student_ids:
                skipped_students = User.objects.filter(id__in=me.skipped_student_ids)
            else:
                skipped_students = []

            form_errors = []
            if me.errors:
                form_errors = list(me.errors)

            context.update(
                {
                    "course_admin_page_title": "Manually Enroll Students : Complete",
                    "enrolled_students": enrolled_students,
                    "moved_students": moved_students,
                    "skipped_students": skipped_students,
                    "invited_users": me.invited_users.all(),
                    "form_errors": form_errors,
                }
            )

        else:
            context["form"] = form

    else:
        form = ManualEnrollmentForm(initial={"course": course})
        context["form"] = form

    Tracker.track(
        event_type=TrackingEventType.COURSE_ADMIN_PAGE_VIEW.value,
        user=request.user,
        event_data={
            "course_admin_tab": "course_enrollment",
            "tab_page": "manual_enrollment",
        },
        course=course,
    )

    return render(request, template_name, context)


@course_staff_required
def invited_users(request, course_run: str, course_slug: str):
    """
    Main view for Course Enrollment section in course.
    """

    course = get_object_or_404(Course, run=course_run, slug=course_slug)

    invite_users = InviteUser.objects.filter(cohort__course=course).all()

    course_admin_breadcrumbs = [
        {
            "label": "Course Enrollment",
            "url": reverse(
                "course:course_admin:course_enrollment:index",
                kwargs={"course_run": course.run, "course_slug": course.slug},
            ),
        },
        {"label": "Invited Users"},
    ]

    context = {
        "course": course,
        "course_slug": course_slug,
        "invite_users": invite_users,
        "course_run": course_run,
        "course_admin_breadcrumbs": course_admin_breadcrumbs,
        "current_course_tab": "course_admin",
        "current_course_tab_name": "Course Admin",
        "current_course_admin_tab": "course_enrollment",
        "course_admin_page_title": "Invited Users",
    }

    Tracker.track(
        event_type=TrackingEventType.COURSE_ADMIN_PAGE_VIEW.value,
        user=request.user,
        event_data={
            "course_admin_tab": "course_enrollment",
            "tab_page": "invited_users",
        },
        course=course,
    )

    return render(request, "course_admin/course_enrollment/invited_users.html", context)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# HTMX VIEW METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@course_staff_required
def delete_invite_user_hx(
    request, course_slug=None, course_run=None, invite_user_id=None
):
    """
    HTMX request. Deletes InviteUser and returns
    list of InvitedUsers to repopulate table.
    """

    course = get_object_or_404(Course, run=course_run, slug=course_slug)

    invite_user = get_object_or_404(
        InviteUser, id=invite_user_id, cohort__course=course
    )

    if invite_user.registered_date:
        raise PermissionDenied(
            f"The invite user {invite_user_id} does not belong to course {course}"
        )

    invite_user.delete()

    invite_users = InviteUser.objects.filter(cohort__course=course).all()

    context = {"course": course, "invite_users": invite_users}
    return render(
        request, "course_admin/course_enrollment/hx/invited_users.html", context
    )
