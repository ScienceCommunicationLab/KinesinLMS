import logging

import factory

from kinesinlms.assessments.models import Assessment, SubmittedAnswer
from kinesinlms.learning_library.constants import AssessmentType, AnswerStatus

logger = logging.getLogger(__name__)


class DoneIndicatorAssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Assessment

    type = AssessmentType.DONE_INDICATOR.name
    slug = factory.Sequence(lambda n: f"assessment-{n}")
    question = factory.Sequence(lambda n: f"Are you done with {n}?")
    has_correct_answer = False
    graded = True


class LongFormAssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Assessment

    type = AssessmentType.LONG_FORM_TEXT.name
    slug = factory.Sequence(lambda n: f"assessment-{n}")
    question = factory.Sequence(lambda n: f"Some long question for question # {n}")
    has_correct_answer = False
    graded = True


class MultipleChoiceAssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Assessment

    type = AssessmentType.MULTIPLE_CHOICE.name
    slug = factory.Sequence(lambda n: f"assessment-{n}")
    question = factory.Sequence(lambda n: (
        f"Which scientist coined the term “cells” from microscopic observations"
        f"of slices of cork? {n}"
    ))
    definition_json = {
        "choices": [
            {"text": "Walther Flemming", "choice_key": "A"},
            {"text": "Robert Hooke", "choice_key": "B"},
            {"text": "Isaac Newton", "choice_key": "C"},
            {"text": "Antonie van Leeuvenhoek", "choice_key": "D"}
        ]
    }
    solution_json = {
        "join": "AND",
        "correct_choice_keys": ["B"]
    }
    has_correct_answer = True
    graded = True


class PollAssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Assessment

    type = AssessmentType.POLL.name
    slug = factory.Sequence(lambda n: f"assessment-{n}")
    question = factory.Sequence(lambda n: f"Do you like {n}?")
    has_correct_answer = False
    graded = False
    definition_json = {
        "choices": [
            {"text": "Walther Flemming", "choice_key": "A"},
            {"text": "Robert Hooke", "choice_key": "B"},
            {"text": "Isaac Newton", "choice_key": "C"},
            {"text": "Antonie van Leeuvenhoek", "choice_key": "D"}
        ]
    }


class SubmittedAnswerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SubmittedAnswer

    status = AnswerStatus.COMPLETE.name
    json_content = {
        "answer": "Some answer text."
    }
