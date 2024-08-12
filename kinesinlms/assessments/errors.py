

from django.core.exceptions import ValidationError


# Custom errors
class TooManyAttemptsError(ValidationError):
    pass


class SubmittedAnswerMissingError(ValidationError):
    pass


class InvalidSubmittedAnswer(ValidationError):
    pass
