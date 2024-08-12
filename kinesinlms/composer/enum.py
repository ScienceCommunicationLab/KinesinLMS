from enum import Enum


class AssessmentCompleteMode(Enum):
    """
    Describes how an Assessment behaves as student
    tries to complete it.
    """

    # Assessment remains enabled after student completes the assessment
    # This is a good setting for assessments where student has to enter
    # something, but may come back and want to refine it later.
    ALWAYS_ENABLED = "Always enabled"

    # If an asssessment becomes 'COMPLETE' or 'CORRECT', it is disabled.
    DISABLED_ON_COMPLETE = "Disabled on complete"


class CopyType(Enum):
    SHALLOW = "shallow"
