"""

"""
import csv
import json
import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Exists, OuterRef
from django.http import HttpResponseForbidden, HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import UpdateView, CreateView

from kinesinlms.cohorts.forms import CohortForm
from kinesinlms.course.models import Course, Cohort, CourseStaff, CohortMembership, CohortType, CoursePassed, \
    CourseStaffRole
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.tracker import Tracker

logger = logging.getLogger(__name__)

User = get_user_model()


@login_required
def index(request, course_run: str, course_slug: str):
    """
    Main view for Course Cohorts section in course.
    """

    course = get_object_or_404(Course, run=course_run, slug=course_slug)
    course_staff_user = None
    if request.user.is_superuser is False and request.user.is_staff is False:
        try:
            course_staff_user = CourseStaff.objects.get(course=course, user=request.user)
        except CourseStaff.DoesNotExist:
            return HttpResponseForbidden()

    selected_id = request.GET.get('id', None)
    selected_slug = request.GET.get('slug', None)
    selected_cohort = None
    students = None
    try:
        if selected_id:
            selected_cohort = course.cohorts.get(id=selected_id)
        elif selected_slug:
            selected_cohort = course.cohorts.get(slug=selected_slug)
        if selected_cohort:
            students = selected_cohort.students.all().annotate(
                has_passed=Exists(CoursePassed.objects.filter(student=OuterRef('pk'))))
    except Cohort.DoesNotExist:
        pass

    if course_staff_user:
        cohorts = course_staff_user.cohorts.all()
    else:
        cohorts = course.cohorts.all()

    context = {
        'course': course,
        'cohorts': cohorts,
        'course_slug': course_slug,
        'course_run': course_run,
        'current_course_tab': 'course_admin',
        'current_course_tab_name': 'Course Admin',
        'current_course_admin_tab': 'course_cohorts',
        'course_admin_page_title': 'Course Cohorts',
        'selected_cohort': selected_cohort,
        'students': students
    }

    Tracker.track(event_type=TrackingEventType.COURSE_ADMIN_PAGE_VIEW.value,
                  user=request.user,
                  event_data={"course_admin_tab": "cohorts",
                              "tab_page": "index"},
                  course=course)

    return render(request,
                  'course_admin/cohorts/index.html',
                  context)


class CreateCohortView(CreateView, LoginRequiredMixin, UserPassesTestMixin):
    model = Cohort
    form_class = CohortForm
    template_name = 'course_admin/cohorts/cohort_form.html'

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def get_initial(self):
        course_run = self.kwargs.get('course_run')
        course_slug = self.kwargs.get('course_slug')
        course = Course.objects.get(run=course_run, slug=course_slug)
        return {'course': course}

    def get_success_url(self):
        course_run = self.kwargs.get('course_run')
        course_slug = self.kwargs.get('course_slug')
        course = Course.objects.get(run=course_run, slug=course_slug)
        success_url = reverse('course:course_admin:cohorts:index',
                              kwargs={"course_run": course.run, "course_slug": course.slug})

        Tracker.track(event_type=TrackingEventType.COURSE_ADMIN_PAGE_VIEW.value,
                      user=self.request.user,
                      event_data={"course_admin_tab": "cohorts",
                                  "tab_page": "create_cohort"},
                      course=course)

        return f"{success_url}?id={self.object.id}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_run = self.kwargs.get('course_run')
        course_slug = self.kwargs.get('course_slug')
        course = Course.objects.get(run=course_run, slug=course_slug)
        additional_context = {
            'course': course,
            'course_slug': course.slug,
            'course_run': course.run,
            'current_course_tab': 'course_admin',
            'current_course_tab_name': 'Course Admin',
            'current_course_admin_tab': 'cohorts',
            'course_admin_page_title': 'Course Cohorts',
        }
        context.update(additional_context)
        return context


class EditCohortView(UpdateView, LoginRequiredMixin, UserPassesTestMixin):
    model = Cohort
    form_class = CohortForm
    pk_url_kwarg = 'cohort_id'
    template_name = 'course_admin/cohorts/cohort_form.html'

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def get_success_url(self):
        course_run = self.kwargs.get('course_run')
        course_slug = self.kwargs.get('course_slug')
        course = Course.objects.get(run=course_run, slug=course_slug)
        success_url = reverse('course:course_admin:cohorts:index',
                              kwargs={"course_run": course.run, "course_slug": course.slug})

        Tracker.track(event_type=TrackingEventType.COURSE_ADMIN_PAGE_VIEW.value,
                      user=self.request.user,
                      event_data={"course_admin_tab": "cohorts",
                                  "tab_page": "edit_cohort"},
                      course=course)

        return f"{success_url}?id={self.object.id}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_run = self.kwargs.get('course_run')
        course_slug = self.kwargs.get('course_slug')
        course = Course.objects.get(run=course_run, slug=course_slug)
        additional_context = {
            'course': course,
            'course_slug': course.slug,
            'course_run': course.run,
            'current_course_tab': 'course_admin',
            'current_course_tab_name': 'Course Admin',
            'current_course_admin_tab': 'cohorts',
            'course_admin_page_title': 'Course Cohorts',
        }
        context.update(additional_context)
        return context


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def create_or_edit_cohort(request, course_run: str, course_slug: str, cohort_id: int):
    course = get_object_or_404(Course, run=course_run, slug=course_slug)
    cohort = None
    if cohort_id:
        cohort = get_object_or_404(Cohort, id=cohort_id, course=course)
        mode = "create"
    else:
        mode = "edit"

    if request.POST:
        form = CohortForm(request.POST)
        if form.is_valid():
            cohort = form.save()
            messages.add_message(request,
                                 messages.INFO,
                                 message=f"Created cohort '{cohort.name}'")
            redirect_url = reverse('course:course_admin:cohorts:index',
                                   kwargs={"course_run": course.run, "course_slug": course.slug})
            return redirect(redirect_url)
        else:
            # Template will display form errors
            pass
    else:
        if cohort:
            form = CohortForm(instance=cohort)
        else:
            form = CohortForm(initial={
                "course": course,
                "name": None,
                "slug": None
            })

    context = {
        'form': form,
        'course': course,
        'mode': mode,
        'course_slug': course_slug,
        'course_run': course_run,
        'current_course_tab': 'course_admin',
        'current_course_tab_name': 'Course Admin',
        'current_course_admin_tab': 'course_cohorts',
        'course_admin_page_title': 'Course Cohorts',
    }
    return render(request,
                  'course_admin/cohorts/cohort_form.html',
                  context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def cohort_delete(request, course_run: str, course_slug: str, cohort_id: int):
    course = get_object_or_404(Course, run=course_run, slug=course_slug)
    cohort = get_object_or_404(Cohort, id=cohort_id, course=course)

    # Add students to default cohort before deleting the cohort...
    default_cohort = Cohort.objects.get(course=course, type=CohortType.DEFAULT.name)
    for student in cohort.students.all():
        membership, created = CohortMembership.objects.get_or_create(student=student, cohort=default_cohort)

    # Now delete cohort and return to list...
    try:
        cohort.delete()
        messages.add_message(request, messages.INFO, f"Deleted cohort '{cohort.name}'")
    except Exception:
        messages.add_message(request, messages.ERROR,
                             f"Could not delete cohort. (But students were reassigned to the DEFAULT cohort.)")

    redirect_url = reverse('course:course_admin:cohorts:index',
                           kwargs={"course_run": course.run, "course_slug": course.slug})

    return redirect(redirect_url)


@login_required
def download_cohort_info(request, course_slug: str, course_run: str, cohort_id: int):
    course = get_object_or_404(Course, run=course_run, slug=course_slug)
    cohort = get_object_or_404(Cohort, id=cohort_id, course=course)

    if request.user.is_superuser is False and request.user.is_staff is False:
        try:
            course_staff_user = CourseStaff.objects.get(course=course, user=request.user,
                                                        role=CourseStaffRole.EDUCATOR.name)
            if not course_staff_user.can_access_cohort(cohort):
                return HttpResponseForbidden()
        except CourseStaff.DoesNotExist:
            return HttpResponseForbidden()

    students = cohort.students.all().annotate(has_passed=Exists(CoursePassed.objects.filter(student=OuterRef('pk'))))

    # Build result
    response = HttpResponse(content_type='text/csv')
    filename = 'cohort_students.csv'
    response['Content-Disposition'] = "attachment; filename=\"{}\"".format(filename)
    writer = csv.writer(response)

    writer.writerow([f"Cohort: {cohort.name}"])

    # write headers
    writer.writerow(['username', 'name', 'email', 'has_passed'])

    # write rows
    for student in students:
        row = [
            student.username,
            student.name,
            student.email,
            student.has_passed
        ]
        writer.writerow(row)

    Tracker.track(event_type=TrackingEventType.COURSE_ADMIN_DOWNLOAD.value,
                  user=request.user,
                  event_data={
                      "download_type": "cohorts",
                      "cohort": cohort.slug
                  },
                  course=course)

    return response


@login_required
def cohort_student(request, course_slug: str, course_run: str, cohort_id: int, student_id: int):
    course = get_object_or_404(Course, run=course_run, slug=course_slug)
    cohort = get_object_or_404(Cohort, id=cohort_id, course=course)
    try:
        student = cohort.students.get(id=student_id)
    except User.DoesNotExist:
        raise Http404(f"No student with id {student_id} in this cohort.")

    if request.user.is_superuser is False and request.user.is_staff is False:
        try:
            course_staff_user = CourseStaff.objects.get(course=course,
                                                        user=request.user,
                                                        role=CourseStaffRole.EDUCATOR.name)
            if not course_staff_user.can_access_cohort(cohort):
                return HttpResponseForbidden()
        except CourseStaff.DoesNotExist:
            return HttpResponseForbidden()

    course_admin_breadcrumbs = [
        {
            'label': 'Course Cohorts',
            'url': reverse('course:course_admin:cohorts:index',
                           kwargs={'course_run': course.run, 'course_slug': course.slug})
        },
        {
            'label': 'Cohort Member',
            'url': None
        }
    ]

    context = {
        'course': course,
        'cohort': cohort,
        'student': student,
        'course_admin_breadcrumbs': course_admin_breadcrumbs,
        'current_course_tab': 'course_admin',
        'current_course_tab_name': 'Course Admin',
        'current_course_admin_tab': 'course_cohorts',
        'course_admin_page_title': 'Cohort Member',
    }

    Tracker.track(event_type=TrackingEventType.COURSE_ADMIN_PAGE_VIEW.value,
                  user=request.user,
                  event_data={"course_admin_tab": "cohorts",
                              "tab_page": "cohort_student"},
                  course=course)

    return render(request,
                  'course_admin/cohorts/cohort_student.html',
                  context)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# HTMX METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@login_required
def cohorts_hx(request, course_slug: str, course_run: str):
    """
    Return a list of cohorts
    """
    course = get_object_or_404(Course, slug=course_slug, run=course_run)

    course_staff_user = None
    if request.user.is_superuser is False and request.user.is_staff is False:
        try:
            course_staff_user = CourseStaff.objects.get(course=course, user=request.user)
        except CourseStaff.DoesNotExist:
            return HttpResponseForbidden()

    if course_staff_user:
        cohorts = course_staff_user.cohorts.all()
    else:
        cohorts = course.cohorts.all()

    context = {
        'course': course,
        'cohorts': cohorts
    }

    return render(request,
                  'course_admin/cohorts/hx/cohort_list_item.html',
                  context)


@login_required
def cohort_hx(request, course_slug: str, course_run: str, cohort_id: int):
    """
    Return a cohort.
    """
    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    cohort = get_object_or_404(Cohort, id=cohort_id, course=course)

    is_active = request.GET.get('active', 'false').upper() == "TRUE"

    if course != cohort.course:
        raise ValueError(f"Cohort is not in course")

    if request.user.is_superuser is False and request.user.is_staff is False:

        # User must be a CourseStaff user...
        try:
            course_staff = CourseStaff.objects.get(course=course, user=request.user)
        except CourseStaff.DoesNotExist:
            return HttpResponseForbidden()

        # ...and you must have access to this cohort
        if not course_staff.cohorts.filter(id=cohort.id).exists():
            return HttpResponseForbidden()

    context = {
        'course': course,
        'cohort': cohort,
        'is_active': is_active
    }

    return render(request,
                  'course_admin/cohorts/hx/cohort_list_item.html',
                  context)


@login_required
def cohort_students_hx(request, course_slug: str, course_run: str, cohort_id: int):
    """
    Return a list of students in a cohort
    """
    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    cohort = get_object_or_404(Cohort, id=cohort_id, course=course)

    if course != cohort.course:
        raise ValueError(f"Cohort is not in course")

    if request.user.is_superuser is False and request.user.is_staff is False:

        # User must be a CourseStaff user...
        try:
            course_staff = CourseStaff.objects.get(course=course, user=request.user)
        except CourseStaff.DoesNotExist:
            return HttpResponseForbidden()

        # ...and you must have access to this cohort
        if not course_staff.cohorts.filter(id=cohort.id).exists():
            return HttpResponseForbidden()

    students = cohort.students.all().annotate(
        has_passed=Exists(CoursePassed.objects.filter(course=course, student=OuterRef('pk'))))

    student_sort = request.GET.get('student_sort', None)
    if student_sort in ["name", "email", "username", "has_passed"]:
        students = students.order_by(student_sort)
        if student_sort == "has_passed":
            students = students.reverse()  # has passed first

    context = {
        'course': course,
        'selected_cohort': cohort,
        'selected_cohort_id': cohort.id,
        'students': students,
        'student_sort': student_sort
    }

    return render(request,
                  'course_admin/cohorts/hx/cohort_detail.html',
                  context)


@login_required
def cohort_move_student_hx(request, course_slug: str, course_run: str, cohort_id: int, student_id: int):
    """
    Move a student to a new cohort
    """
    try:
        course = Course.objects.get(slug=course_slug, run=course_run)
        new_cohort = Cohort.objects.get(id=cohort_id, course=course)
        student = User.objects.get(id=student_id)
        current_cohort_membership = CohortMembership.objects.get(student=student, cohort__course=course)
    except Exception:
        raise Http404()

    if request.user.is_superuser is False and request.user.is_staff is False:

        # User must be a CourseStaff user...
        try:
            course_staff = CourseStaff.objects.get(course=course, user=request.user)
        except CourseStaff.DoesNotExist:
            return HttpResponseForbidden()

        # ...and you must have access to old cohort and new cohort
        if not course_staff.cohorts.filter(id=current_cohort_membership.cohort.id).exists():
            return HttpResponseForbidden()
        if not course_staff.cohorts.filter(id=new_cohort.id).exists():
            return HttpResponseForbidden()

    # student must already belong to a cohort
    current_cohort_membership.cohort = new_cohort
    current_cohort_membership.save()

    context = {
        'course': course,
        'cohort': new_cohort
    }

    if new_cohort.type == CohortType.DEFAULT.name:
        new_cohort_name = "the 'unassigned' cohort"
    else:
        new_cohort_name = new_cohort.name

    move_message = f"Moved student '{student.username}' to cohort '{new_cohort_name}'"
    headers = {
        'HX-Trigger': json.dumps({
            "moveStudentToNewCohortMessage": move_message
        })
    }
    response = render(request,
                      'course_admin/cohorts/hx/cohort_list_item.html',
                      context)
    response.headers = headers
    return response
