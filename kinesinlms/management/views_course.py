import logging

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, resolve_url, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, UpdateView

from kinesinlms.badges.models import BadgeClass, BadgeAssertion
from kinesinlms.course.models import Course, CourseUnit, Enrollment
from kinesinlms.management.forms import DeleteCourseForm, \
    DuplicateCourseForm, UpdateCourseForm
from kinesinlms.users.mixins import SuperuserRequiredMixin

logger = logging.getLogger(__name__)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# VIEW CLASSES
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class CourseListView(SuperuserRequiredMixin, ListView):
    model = Course
    template_name = 'management/courses/courses_list.html'
    context_object_name = 'courses'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        extra_context = {
            "breadcrumbs": [
                {
                    "label": "Management",
                    "url": reverse('management:index')
                }
            ],
            "section": "management",
            "title": "Courses",
            "description": "List of all courses",
        }
        context.update(extra_context)
        return context


class CourseUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Course
    template_name = 'management/courses/course_update.html'
    context_object_name = 'course'
    form_class = UpdateCourseForm

    def form_valid(self, form):
        messages.success(self.request, "Course updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        success_url = reverse_lazy('management:course_update',
                                   kwargs={
                                       'course_slug': self.object.slug,
                                       'course_run': self.object.run
                                   })
        return success_url

    def get_object(self, queryset=None):
        course_slug = self.kwargs.get('course_slug')
        course_run = self.kwargs.get('course_run')
        return get_object_or_404(Course, slug=course_slug, run=course_run)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        extra_context = {
            "breadcrumbs": [
                {
                    "label": "Management",
                    "url": reverse('management:index')
                },
                {
                    "label": "Courses",
                    "url": reverse('management:courses_list')
                }
            ],
            "section": "management",
            "title": "Edit Course",
            "description": "Edit an exising course",
        }
        context.update(extra_context)
        return context


class CourseBadgeAssertionListView(SuperuserRequiredMixin, ListView):
    model = BadgeClass
    template_name = 'management/courses/badges/course_badge_assertions_list.html'
    context_object_name = 'badge_assertions'

    def get_queryset(self):
        # Get the values of course_slug and course_run from the URL
        course_slug = self.kwargs['course_slug']
        course_run = self.kwargs['course_run']

        # Filter the queryset based on course_slug and course_run
        queryset = BadgeAssertion.objects.filter(
            badge_class__course__slug=course_slug,
            badge_class__course__run=course_run
        )

        return queryset

    def get_context_data(self, **kwargs):
        course_slug = self.kwargs['course_slug']
        course_run = self.kwargs['course_run']
        course = Course.objects.get(slug=course_slug, run=course_run)

        context = super().get_context_data(**kwargs)
        extra_context = {
            "breadcrumbs": [
                {
                    "label": "Management",
                    "url": reverse('management:index')
                },
                {
                    "label": "Courses",
                    "url": reverse('management:courses_list')
                },
                {
                    "label": f"Course {course.token}",
                    "url": reverse('management:courses_list')
                }
            ],
            "section": "management",
            "title": "Awarded Badges",
            "description": "A list of badges awarded in this course.",
        }
        context.update(extra_context)
        return context


class CourseBadgeClassListView(SuperuserRequiredMixin, ListView):
    model = BadgeClass
    template_name = 'management/courses/badges/course_badge_classes_list.html'
    context_object_name = 'badge_classes'

    def get_queryset(self):
        # Get the values of course_slug and course_run from the URL
        course_slug = self.kwargs['course_slug']
        course_run = self.kwargs['course_run']

        # Filter the queryset based on course_slug and course_run
        queryset = BadgeClass.objects.filter(
            course__slug=course_slug,
            course__run=course_run
        )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_slug = self.kwargs['course_slug']
        course_run = self.kwargs['course_run']
        course = Course.objects.get(slug=course_slug, run=course_run)
        extra_context = {
            "breadcrumbs": [
                {
                    "label": "Management",
                    "url": reverse('management:index')
                },
                {
                    "label": "Courses",
                    "url": reverse('management:courses_list')
                },
                {
                    "label": f"Course {course.token}",
                    "url": reverse('management:courses_list')
                }
            ],
            "section": "management",
            "title": "Badge Classes",
            "description": "Manage badge classes defined for this course.",
        }
        context.update(extra_context)
        return context


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# VIEW METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@user_passes_test(lambda u: u.is_superuser)
def students_in_course_list(request, course_slug: str, course_run: str):
    """

    List all students in a course in a template that provides access to
    management functions for each student.

    Args:
        request:
        course_slug:
        course_run:

    Returns:
        HTTP response
    """

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    enrollments = Enrollment.objects.filter(course=course)
    context = {
        "enrollments": enrollments,
        "fluid_info_bar": True,
        "course": course,
        "section": "management",
        "title": f"Manage Students in {course.token}",
        "breadcrumbs": [
            {
                "url": f"/management/courses",
                "label": "Manage Courses"
            },
            {
                "label": "Courses",
                "url": reverse('management:courses_list')
            }
        ]
    }

    return render(request, "management/students/students_in_course_list.html", context)


@user_passes_test(lambda u: u.is_superuser)
def duplicate_course(request, course_slug=None, course_run=None):
    """
    Allows user to copy a selected course and create a new one
    with same properties.

    The user can modify a few of the course's properties before the copy
    happens (such as self_paced), mostly properties that directly
    affect how the copy will happen.

    However, most properties are copied as-is and are
    meant to be modified once the copy is complete.


    Args:
        request:
        course_slug:
        course_run:

    Returns
        HTTP response
    """

    if not request.user.is_superuser:
        return HttpResponseForbidden()

    course = get_object_or_404(Course, slug=course_slug, run=course_run)

    if request.POST:
        form = DuplicateCourseForm(request.POST)
        if not form.is_valid():
            raise Exception("Invalid form")
    else:
        # Make sure to change key props, so we indicate this is a dup.
        initial = {"slug": f"{course.slug}_COPY"}
        form = DuplicateCourseForm(instance=course, initial=initial)

    context = {
        "course": course,
        "form": form,
        "section": "management",
        "title": f"Duplicate course {course.token}",
        "breadcrumbs": [
            {
                "url": reverse('management:index'),
                "label": "Management"
            },

            {
                "label": "Courses",
                "url": reverse('management:courses_list')
            }
        ]
    }

    return render(request, template_name="management/courses/course_duplicate.html", context=context)


@user_passes_test(lambda u: u.is_superuser)
def delete_course(request, course_slug=None, course_run=None):
    """
    This view deletes a course.
    It also deletes resources like Blocks that
    don't naturally delete via a CASCADE, if the user indicated
    they really want to delete *everything* related with a course.

    This is really only for the super, and probably really only
    during development when you want to get rid of a course in development
    and try again from scratch.

    One probably doesn't want to delete courses on a live system that will
    be mentioned in things like tracking events. Probably better to simply
    deactivate them.

    Args:
        request:
        course_slug:
        course_run:

    Returns
        HTTP response
    """

    if not request.user.is_superuser:
        return HttpResponseForbidden()

    course = get_object_or_404(Course, slug=course_slug, run=course_run)
    course_token = course.token
    course_id = course.id

    try:

        form = DeleteCourseForm(request.POST)
        if not form.is_valid():
            raise Exception("Invalid form")

        # delete catalog
        course.catalog_description.delete()

        if form.cleaned_data['delete_blocks']:
            # delete blocks
            course_units = CourseUnit.objects.filter(course_id=course_id)
            for course_unit in course_units:
                for block in course_unit.contents.all():
                    course_unit.contents.remove(block)
                    if len(block.units.all()) == 0:
                        block.delete()

        # delete
        course.delete()

        msg = f"Deleted course {course_token}"
        messages.add_message(request, messages.INFO, msg)
        courses_list_url = resolve_url("management:courses_list")

    except Exception as e:

        msg = f"Could not delete course {course_token} : {e}"
        messages.add_message(request, messages.ERROR, msg)
        courses_list_url = resolve_url("management:courses_list")

    return redirect(courses_list_url)
