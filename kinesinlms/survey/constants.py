from enum import Enum


class SurveyType(Enum):
    """
    Describes the nature of the survey in relation to the
    course it appears in. Some survey's, like FOLLOW_UP, might
    not appear in an actual unit (but instead just be emailed
    to a user after a certain time after the student passed the
    course).

    (At the moment, no real functionality is attached to this type.
    It's more to just annotate the purpose of a survey.)
    """
    BASIC = "basic"
    PRE_COURSE = "pre-course"
    POST_COURSE = "post-course"
    FOLLOW_UP = "follow-up"

    def __str__(self):
        return self.name


class SurveyEmailStatus(Enum):
    """ The different states a survey email task can be in. """
    UNPROCESSED = 'unprocessed'
    SENT = 'sent'
    ERROR = 'error'

    def __str__(self):
        return self.name
