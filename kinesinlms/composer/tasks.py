from time import sleep
from typing import Tuple

from celery.utils.log import get_task_logger

from config import celery_app
from kinesinlms.composer.import_export.ibiov2.importer import IBiologyCoursesCourseImporter
from kinesinlms.composer.import_export.importer import (
    CourseImporterBase,
    CourseImportOptions,
)
from kinesinlms.composer.import_export.kinesinlms.importer import KinesinLMSCourseImporter
from kinesinlms.composer.models import CourseImportTaskResult, CourseImportTaskStatus

logger = get_task_logger(__name__)


def handle_course_import_failure(self, exc: Exception, task_id: str, args: Tuple, kwargs: dict, einfo: str) -> None:
    """
    Handles exceptions that occur when generate_course_import fails to complete after retries.

    Args:
        self: Celery task instance
        exc: The exception that occurred
        task_id: Celery task ID
        args: Task positional arguments
        kwargs: Task keyword arguments
        einfo: Error information
    """
    logger.error(
        "COURSE REPORT GENERATION FAILURE:\n"
        f"Task: {self}\n"
        f"Task ID: {task_id}\n"
        f"Exception: {exc}\n"
        f"Args: {args}\n"
        f"Kwargs: {kwargs}\n"
        f"Error Info: {einfo}"
    )

    course_token = kwargs.get("course_token")
    report_type = kwargs.get("report_type")

    if course_token and report_type:
        course_report, _ = CourseImportTaskResult.objects.get_or_create(
            course_token=course_token, report_type=report_type
        )
        course_report.generation_status = CourseImportTaskStatus.FAILED.name
        course_report.error_message = str(exc)
        course_report.save()


@celery_app.task(
    bind=True,
    autoretry_for=(CourseImportTaskResult.DoesNotExist,),
    retry_backoff=True,
    time_limit=360,  # 6 minutes
    soft_time_limit=300,  # 5 minutes
    retry_kwargs={"max_retries": 3},
    on_failure=handle_course_import_failure,
)
def generate_course_import_task(
    self,
    course_import_task_result_id: int,
    ignore_staff_data: bool = False,
) -> bool:
    """
    Generates a course import given an import file.

    Args:
        self: Celery task instance
        course_import_task_result_id: Unique course identifier in format "slug_run"

    Returns:
        bool: True if report generation successful

    Raises:
        Exception: If report type is unsupported
        CourseImportTaskResult.DoesNotExist: If course report cannot be found/created
    """
    logger.info("Generating course report:\n" f"CourseImportTaskResult ID: {course_import_task_result_id}")

    # Parse course token
    course_import_task = CourseImportTaskResult.objects.get(id=course_import_task_result_id)
    course_import_task.generation_status = CourseImportTaskStatus.IN_PROGRESS.name
    course_import_task.save()

    # Check extension to decide which importer class to use
    if course_import_task.import_file.name.endswith(".ibioarchive"):
        importer: CourseImporterBase = IBiologyCoursesCourseImporter()
    else:
        # Assume KinesinLMS format
        importer: CourseImporterBase = KinesinLMSCourseImporter()

    # Temp
    sleep(10)

    try:
        options = CourseImportOptions(create_forum_items=course_import_task.create_forum_items)
        course = importer.import_course_from_archive(
            file=course_import_task.import_file,
            display_name=course_import_task.display_name,
            course_slug=course_import_task.course_slug,
            course_run=course_import_task.course_run,
            options=options,
        )
    except Exception as e:
        logger.error(f"Course import failed: {e}")
        course_import_task.generation_status = CourseImportTaskStatus.FAILED.name
        course_import_task.error_message = str(e)
        course_import_task.save()
        return False

    logger.info(f"Course import successful: {course}")
    course_import_task.course = course
    course_import_task.generation_status = CourseImportTaskStatus.COMPLETED.name
    course_import_task.save()

    return True
