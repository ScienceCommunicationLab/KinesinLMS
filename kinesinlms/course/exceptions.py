class CourseFinishedException(Exception):
    """
    MilestoneMonitor raises this exception if a course
    is finished. No tracking will be done in this case.
    """
    pass
