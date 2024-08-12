import csv
import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.timezone import now

from config import celery_app
from kinesinlms.core.constants import TaskResult
from kinesinlms.core.decorators import course_staff_required
from kinesinlms.course.models import (
    CohortMembership,
    Course,
    CourseStaff,
    CourseStaffRole,
    Cohort,
)
from kinesinlms.course_analytics.charts import (
    get_enrollments_chart,
    get_course_passed_chart,
    get_engagement_chart,
)
from kinesinlms.course_analytics.models import StudentProgressReport
from kinesinlms.course_analytics.tasks import start_student_progress_report_task
from kinesinlms.course_analytics.utils import BarColors
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.tracker import Tracker

logger = logging.getLogger(__name__)

User = get_user_model()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# VIEW CLASSES
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ( none yet ...)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# VIEW METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@course_staff_required
def index(request, course_run: str, course_slug: str):
    """
    Main view for Course Analytics section in course.
    """

    # Make sure educator has access to this course

    course = get_object_or_404(Course, run=course_run, slug=course_slug)
    cohort_id = request.GET.get("cohort_id", None)

    allowed_all_cohorts = False
    if request.user.is_superuser or request.user.is_staff:
        allowed_all_cohorts = True
        cohorts = course.cohorts.all()
    else:
        try:
            course_staff_user = CourseStaff.objects.get(
                course=course, user=request.user, role=CourseStaffRole.EDUCATOR.name
            )
            cohorts = course_staff_user.cohorts.all()
        except CourseStaff.DoesNotExist:
            return HttpResponseForbidden()

    current_cohort = None
    if cohort_id:
        try:
            current_cohort = cohorts.get(id=cohort_id)
        except Cohort.DoesNotExist:
            pass

    engagement_chart = get_engagement_chart(course=course, cohort=current_cohort)

    enrollments_chart = get_enrollments_chart(
        course=course, cohort=current_cohort, bar_color="#467291"
    )

    course_passed_chart = get_course_passed_chart(
        course=course, cohort=current_cohort, bar_color="#45916f"
    )

    Tracker.track(
        event_type=TrackingEventType.COURSE_ADMIN_PAGE_VIEW.value,
        user=request.user,
        event_data={"course_admin_tab": "course_analytics", "tab_page": "index"},
        course=course,
    )

    context = {
        "course": course,
        "course_slug": course_slug,
        "course_run": course_run,
        "cohorts": cohorts,
        "enrollments_chart": enrollments_chart,
        "course_passed_chart": course_passed_chart,
        "engagement_chart": engagement_chart,
        "current_course_tab": "course_admin",
        "current_course_tab_name": "Course Admin",
        "current_course_admin_tab": "course_analytics",
        "course_admin_page_title": "Course Analytics",
        "current_cohort": current_cohort,
        "alllowed_all_cohorts": allowed_all_cohorts,
    }

    return render(request, "course_admin/course_analytics/index.html", context)


@course_staff_required
def student_progress(
    request,
    course_run: str,
    course_slug: str,
    cohort_id: int = None,
):
    """
    Details on student progress in course. Displays the results if a report
    has been run. Otherwise, displays a "Generate" button.

    Args:
        request:
        course_run:
        course_slug:
        cohort_id:      ID of cohort for report. If NONE, assume 'all cohorts'

    """

    course = get_object_or_404(Course, run=course_run, slug=course_slug)

    # Clear out ungenerated and error reports
    StudentProgressReport.objects.filter(
        user=request.user,
        course=course,
        task_result__in=[TaskResult.UNGENERATED.name, TaskResult.FAILED.name],
    ).delete()

    # Clear out IN_PROGRESS from more than 20 minutes ago
    StudentProgressReport.objects.filter(
        user=request.user,
        course=course,
        created_at__lt=now() - timedelta(minutes=20),
        task_result=TaskResult.IN_PROGRESS.name,
    ).delete()

    try:
        student_progress_report = StudentProgressReport.objects.filter(
            user=request.user, course=course, cohort_id=cohort_id
        ).latest()
    except StudentProgressReport.DoesNotExist:
        student_progress_report = None

    # Determine which cohorts user is allowed to see,
    # and whether they can see all cohorts.
    if request.user.is_superuser or request.user.is_staff:
        cohorts = course.cohorts
    else:
        try:
            course_staff_user = CourseStaff.objects.get(
                course=course, user=request.user, role=CourseStaffRole.EDUCATOR.name
            )
            cohorts = course_staff_user.cohorts
        except CourseStaff.DoesNotExist:
            return HttpResponseForbidden()

    try:
        current_cohort = cohorts.get(id=cohort_id)
    except Cohort.DoesNotExist:
        current_cohort = None

    bar_colors = BarColors()
    course_admin_breadcrumbs = [
        {
            "label": "Course Analytics",
            "url": reverse(
                "course:course_admin:course_analytics:index",
                kwargs={"course_run": course.run, "course_slug": course.slug},
            ),
        },
        {"label": "Student Progress", "url": None},
    ]

    context = {
        "course": course,
        "student_progress_report": student_progress_report,
        "course_admin_breadcrumbs": course_admin_breadcrumbs,
        "course_slug": course_slug,
        "course_run": course_run,
        "cohorts": cohorts.all(),
        "current_cohort": current_cohort,
        "current_course_tab": "course_admin",
        "current_course_tab_name": "Course Admin",
        "current_course_admin_tab": "course_analytics",
        "course_admin_page_title": "Student Progress",
        "bar_colors": bar_colors,
        "num_cohorts": cohorts.count(),
    }

    Tracker.track(
        event_type=TrackingEventType.COURSE_ADMIN_PAGE_VIEW.value,
        user=request.user,
        event_data={
            "course_admin_tab": "course_analytics",
            "tab_page": "student_progress",
        },
        course=course,
    )

    return render(
        request, "course_admin/course_analytics/student_progress.html", context
    )


@course_staff_required
def student_progress_report_cancel(
    request,
    course_run: str,
    course_slug: str,
    pk: int,
):
    course = get_object_or_404(Course, run=course_run, slug=course_slug)

    try:
        report = StudentProgressReport.objects.get(id=pk, user=request.user)
    except StudentProgressReport.DoesNotExist:
        report = None

    reports = StudentProgressReport.objects.filter(course=course, user=request.user)
    for report in reports:
        if report.celery_task_id:
            celery_app.control.revoke(task_id=report.celery_task_id, terminate=True)
        report.delete()

    if report and report.cohort:
        redirect_url = reverse(
            "course:course_admin:course_analytics:student_cohort_progress",
            kwargs={
                "course_run": course.run,
                "course_slug": course.slug,
                "cohort_id": report.cohort.id,
            },
        )

    else:
        redirect_url = reverse(
            "course:course_admin:course_analytics:student_progress",
            kwargs={"course_run": course.run, "course_slug": course.slug},
        )

    messages.add_message(request, messages.INFO, "Report cancelled")
    return redirect(redirect_url)


@course_staff_required
def student_progress_report_download(
    request,
    course_run: str,
    course_slug: str,
    pk: int,
):
    """
    Details on student progress in course as csv file.

    Args:
        request:
        course_run:
        course_slug:
        pk:                 ID of cohort for report. If NONE, assume 'all cohorts'

    """

    course = get_object_or_404(Course, run=course_run, slug=course_slug)

    try:
        student_progress_report = StudentProgressReport.objects.get(
            id=pk, user=request.user
        )
    except StudentProgressReport.DoesNotExist:
        raise Http404()

    # Determine which cohorts user is allowed to see,
    # and whether they can see all cohorts.
    if request.user.is_superuser or request.user.is_staff:
        cohorts = course.cohorts
    else:
        try:
            course_staff_user = CourseStaff.objects.get(
                course=course, user=request.user, role=CourseStaffRole.EDUCATOR.name
            )
            cohorts = course_staff_user.cohorts
        except CourseStaff.DoesNotExist:
            return HttpResponseForbidden()

    Tracker.track(
        event_type=TrackingEventType.COURSE_ADMIN_DOWNLOAD.value,
        user=request.user,
        event_data={"report": "student_progress", "cohorts": cohorts},
        course=course,
    )

    # Create CSV from report
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=student_progress_report.csv"
    writer = csv.writer(response)

    writer.writerow(["Students", student_progress_report.num_students])
    writer.writerow(["Generated on", student_progress_report.generation_date])

    header_1_row = ["", "", "", "", "", "", "", ""]

    header_2_row = [
        "ID",
        "Name",
        "Email",
        "Username",
        "Is Course Staff",
        "Cohort",
        "Career Stage",
        "Has Passed",
    ]

    module_cols = [
        "Units Viewed",
        "Total Units in Module",
        "% Units Viewed",
        "Watched Videos",
        "Total Videos in Module",
        "% Videos Viewed",
        "Answered Assessments",
        "Total Assessments in Module",
        "% Assessments Answered",
        "Answered Sits",
        "Total Sits in Module",
        "% Sits Answered",
        "Answered Surveys",
        "Total Surveys in Module",
        "% Surveys Answered",
    ]
    num_module_cols = len(module_cols) - 1

    for module_info in student_progress_report.modules_info:
        header_1_row.append(f"Module {module_info.display_sequence}")
        header_1_row.extend([" "] * num_module_cols)

        module_name = f"M{module_info.display_sequence}"
        for module_col in module_cols:
            col_name = f"{module_name} {module_col}"
            header_2_row.append(col_name)

    writer.writerow(header_1_row)
    writer.writerow(header_2_row)

    # cohort lookup to avoid multiple DB queries later
    student_cohort_lookup = {}
    for cohort_membership in CohortMembership.objects.filter(cohort__course=course):
        student_cohort_lookup[cohort_membership.student.id] = (
            cohort_membership.cohort.name
        )

    # course staff lookup to avoid multiple DB queries later
    course_staff_ids = list(
        CourseStaff.objects.filter(course=course).values_list("user_id", flat=True)
    )

    for smsp in student_progress_report.students_modules_progresses:
        student = User.objects.get(id=smsp.student_id)
        is_course_staff = smsp.student_id in course_staff_ids
        try:
            cohort_name = student_cohort_lookup[student.id]
        except KeyError:
            logger.error(f"Could not find cohort for student {student.id}")
            cohort_name = ""

        data_row = []
        data_row.extend(
            [
                smsp.student_id,
                smsp.name or "( no name )",
                smsp.email,
                smsp.username,
                is_course_staff,
                cohort_name,
                student.career_stage_name,
                smsp.has_passed,
            ]
        )
        for module_progress in smsp.modules_progress:
            module_name = f"Module {module_progress.module_info.content_index}"
            data_row.extend(
                [
                    module_progress.units_viewed,
                    module_progress.total_units_in_module,
                    module_progress.units_viewed_percent_complete,
                    module_progress.watched_videos,
                    module_progress.total_videos_in_module,
                    module_progress.videos_percent_complete,
                    module_progress.answered_assessments,
                    module_progress.total_assessments_in_module,
                    module_progress.assessments_percent_complete,
                    module_progress.answered_sits,
                    module_progress.total_sits_in_module,
                    module_progress.sits_percent_complete,
                    module_progress.surveys_completed,
                    module_progress.total_surveys_in_module,
                    module_progress.surveys_percent_complete,
                ]
            )
        writer.writerow(data_row)
    return response


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# HTMx Methods
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@course_staff_required
def student_progress_report_state_hx(
    request,
    course_run: str,
    course_slug: str,
    pk: int,
):
    report = get_object_or_404(StudentProgressReport, id=pk, user=request.user)

    context = {
        "student_progress_report": report,
        "current_cohort": report.cohort,
        "course": report.course,
        "bar_colors": BarColors(),
    }
    # Return the student_progress_report template, which knows what partial to
    # show based on the state of the report. Might be the progress bar, might be error,
    # might be final results.
    return render(
        request,
        "course_admin/course_analytics/hx/student_progress_report.html",
        context,
    )


@course_staff_required
def student_progress_generate_hx(
    request,
    course_run: str,
    course_slug: str,
    cohort_id: int = None,
):
    """
    Start the async generation a student progress report.
    Return partial htmx template to show status of task.

    Args:
        request:
        course_run:
        course_slug:
        cohort_id:      ID of cohort for report. If NONE, assume 'all cohorts'

    """

    course = get_object_or_404(Course, run=course_run, slug=course_slug)

    # Determine which set of cohorts user is allowed to see.
    if request.user.is_superuser or request.user.is_staff:
        # ...can see all cohorts...
        cohorts = course.cohorts
    else:
        try:
            course_staff_user = CourseStaff.objects.get(
                course=course, user=request.user, role=CourseStaffRole.EDUCATOR.name
            )
            # course staff users can only see cohorts they've been given access to.
            cohorts = course_staff_user.cohorts
        except CourseStaff.DoesNotExist:
            return HttpResponseForbidden()

    current_cohort = None
    if cohort_id:
        try:
            current_cohort = cohorts.get(id=cohort_id)
        except Cohort.DoesNotExist:
            raise Http404()

    # Clear out any earlier instances
    try:
        for spr in StudentProgressReport.objects.filter(
            user=request.user, course=course, cohort=current_cohort
        ).all():
            if spr.celery_task_id:
                celery_app.control.revoke(task_id=spr.celery_task_id, terminate=True)
            spr.delete()
    except Exception:
        logger.exception("Could not delete old StudentProgressReports.")

    student_progress_report = StudentProgressReport.objects.create(
        user=request.user, course=course, cohort=current_cohort
    )

    task_id = start_student_progress_report_task(student_progress_report)
    logger.info(f"Started task to generate student progress report. Task ID: {task_id}")

    context = {
        "course": course,
        "current_cohort": current_cohort,
        "student_progress_report": student_progress_report,
    }

    Tracker.track(
        event_type=TrackingEventType.COURSE_ADMIN_REPORT_GENERATED.value,
        user=request.user,
        event_data={"report": "student_progress"},
        course=course,
    )

    return render(
        request,
        "course_admin/course_analytics/hx/student_progress_report.html",
        context,
    )
