import logging
import time

from celery.result import AsyncResult
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from django.utils.translation import gettext as _

from config import celery_app
from kinesinlms.core.constants import TaskResult
from kinesinlms.course.models import CourseStaff, CourseStaffRole
from kinesinlms.course_analytics.models import StudentProgressReport
from kinesinlms.course_analytics.utils import get_student_module_progress

User = get_user_model()
logger = logging.getLogger(__name__)


def start_student_progress_report_task(student_progress_report: StudentProgressReport) -> int:
    """
    Sets up and starts an async Celery task to generate a student progress report.

    An important part of this method is to set the StudentProgressReport's state
    to IN_PROGRESS.

    Args:
       student_progress_report:

    Returns:
       task ID (int) for asynchronous task.
    """

    # Now call async task. The task will save the result of its effort in
    # the StudentProgressReport instance. We don't really track results through
    # individual celery task ids, just the final 'goal' of a completed generation in the
    # StudentProgressReport model's generation_result property.
    logger.info(
        f"start_building_analytics_task() : starting new async task "
        f"for StudentProgressReport {student_progress_report.id}"
    )
    async_result: AsyncResult = generate_student_progress_report.apply_async(
        args=[], kwargs={"student_progress_report_id": student_progress_report.id}, countdown=5
    )  # Give DB a chance to complete this transaction

    student_progress_report.task_result = TaskResult.IN_PROGRESS.name
    student_progress_report.task_message = "Starting report process..."
    student_progress_report.task_id = async_result.task_id
    student_progress_report.save()

    logger.info(
        f"start_building_analytics_task() : async task for StudentProgressReport "
        f"started. ID: {async_result.task_id}"
    )

    return async_result.task_id


def generate_student_progress_report_error_handler(self, exc, task_id, args, kwargs, einfo):  # noqa: F841
    """
    Handle errors from task.
    """
    student_progress_report_id = kwargs.get("student_progress_report_id", None)
    logger.error(
        f"generate_student_progress_report_error_handler() "
        f"Error handler called when generating report : {student_progress_report_id}"
    )
    try:
        portfolio_analytics = StudentProgressReport.objects.get(pk=student_progress_report_id)
    except StudentProgressReport.DoesNotExist:
        return

    portfolio_analytics.generation_result = TaskResult.FAILED.name
    portfolio_analytics.task_message = str(exc)
    portfolio_analytics.save()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception, StudentProgressReport.DoesNotExist),
    retry_kwargs={"max_retries": 3},
    countdown=5,
    retry_backoff=True,
    on_failure=generate_student_progress_report_error_handler,
)
def generate_student_progress_report(self, student_progress_report_id):
    """
    Generate the student progress report and save results.
    """
    logger.debug(
        f"TASK generate_student_progress_report(): Task id: {self.request.id} : Running analytics task "
        f"for student progress report ID: {student_progress_report_id}"
    )

    start_time = time.time()

    # Allow DoesNotExist error to bubble up
    try:
        student_progress_report = StudentProgressReport.objects.get(id=student_progress_report_id)
    except StudentProgressReport.DoesNotExist as dne:
        logger.info(
            f"Cannot find StudentProgressReport id {student_progress_report_id}. Raising exception so task waits and tries again..."
        )
        raise dne

    course = student_progress_report.course
    cohort = student_progress_report.cohort
    user = student_progress_report.user

    try:
        if cohort:
            students = cohort.students
        else:
            if user.is_superuser or user.is_staff:
                students = User.objects.filter(enrollments__course=course, enrollments__active=True)
            else:
                course_staff_user = CourseStaff.objects.get(
                    course=course, user=user, role=CourseStaffRole.EDUCATOR.name
                )
                # course staff users can only see cohorts they've been given access to.
                cohorts = course_staff_user.cohorts.all()
                students = User.objects.filter(members__in=cohorts).distinct()

    except Exception:
        error_message = f"Could not collect students for report."
        logger.exception(error_message)
        logger.error(error_message)
        save_result(
            student_progress_report=student_progress_report,
            task_result=TaskResult.FAILED.name,
            task_message=error_message,
        )
        return

    students = students.filter(is_staff=False, is_superuser=False, is_educator=False, is_test_user=False)
    student_progress_report.num_students = len(students)

    def progress_callback(progress_message: str, percent_complete: int = None):
        student_progress_report.task_message = progress_message
        if percent_complete and 0 <= percent_complete <= 100:
            if isinstance(percent_complete, float):
                percent_complete = int(percent_complete)
            student_progress_report.percent_complete = percent_complete
        student_progress_report.save()

    try:
        modules_info, students_modules_progresses = get_student_module_progress(
            student_progress_report.course, students, progress_callback=progress_callback
        )
    except Exception:
        error_message = f"Error generating report"
        logger.exception(error_message)
        logger.error(error_message)
        save_result(
            student_progress_report=student_progress_report,
            task_result=TaskResult.FAILED.name,
            task_message=error_message,
        )
        return

    duration = round(time.time() - start_time, 4)
    try:
        task_message = _("No errors. Duration : {} seconds.".format(duration))
        student_progress_report.modules_info_json = [module_info.to_dict() for module_info in modules_info]
        student_progress_report.students_modules_progresses_json = [
            smp.to_dict() for smp in students_modules_progresses
        ]
        student_progress_report.task_result = TaskResult.COMPLETE.name
        student_progress_report.task_message = task_message
        student_progress_report.generation_date = now()
        student_progress_report.save()
    except Exception:
        save_result(
            student_progress_report=student_progress_report,
            task_result=TaskResult.FAILED.name,
            task_message="Could not save final results",
        )
    return


def save_result(
    student_progress_report: StudentProgressReport, task_result: str, task_message: str
) -> StudentProgressReport:
    student_progress_report.task_result = task_result
    student_progress_report.task_message = task_message
    student_progress_report.generation_date = now()
    student_progress_report.save()
    return student_progress_report
