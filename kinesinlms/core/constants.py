"""
Defines project-wide constants and related data structures (Enum)
"""
from enum import Enum


class SiteFeatures(Enum):
    """
    Enumerates the different features of the site,
    mainly so they can be standardized when used
    with django-waffle. These settings can be controlled in the 
    management UI, in the Django admin panel, or via the command line.
    """
    LEARNING_LIBRARY = 'Learning Library'
    COMPOSER = 'Composer'
    
    # This is the site-wide feature for showing/hiding the speakers page
    # Showing a "Speakers" tab in a course is controlled by the 'speakers'
    # custom app for a course.
    SPEAKERS = 'Speakers'

    # These are testimonials for the whole site
    # Testimonials for each course are stored in the course model
    TESTIMONIALS = 'Testimonials'


class ForumProviderType(Enum):
    """
    Types of forum supported by the system.
    """
    # Only one kind of forum provider at the moment...
    DISCOURSE = "Discourse"


class TaskResult(Enum):
    """
    Standard states for a process handled by a celery task.
    """

    # UNGENERATED means the system has not yet started an async
    # task to generate a result.
    UNGENERATED = "Ungenerated"

    # IN_PROGRESS means the async task is currently generating the results.
    IN_PROGRESS = "In progress"

    # COMPLETE means the async task completed successfully
    COMPLETE = "Complete"

    # FAILED means the asycn task failed for some reason.
    FAILED = "Failed"
