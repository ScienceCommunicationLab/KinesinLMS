from django.test import TestCase

from kinesinlms.assessments.tests.factories import LongFormAssessmentFactory, SubmittedAnswerFactory
from kinesinlms.assessments.utils import delete_submitted_answers, get_answer_data
from kinesinlms.course.tests.factories import BlockFactory, CourseFactory
from kinesinlms.learning_library.constants import BlockType
from kinesinlms.users.tests.factories import UserFactory


class TestAssessmentsUtils(TestCase):
    """
    Test the Assessment utility methods.
    """
    def setUp(self):
        super().setUp()

        self.student1 = UserFactory()
        self.student2 = UserFactory()
        self.course = CourseFactory()
        self.block1 = BlockFactory(type=BlockType.ASSESSMENT.name)
        self.block2 = BlockFactory(type=BlockType.ASSESSMENT.name)
        self.assessment1 = LongFormAssessmentFactory(block=self.block1)
        self.assessment2 = LongFormAssessmentFactory(block=self.block2)
        SubmittedAnswerFactory(
            course=self.course,
            assessment=self.assessment1,
            student=self.student1,
        )
        SubmittedAnswerFactory(
            course=self.course,
            assessment=self.assessment2,
            student=self.student1,
        )
        SubmittedAnswerFactory(
            course=self.course,
            assessment=self.assessment2,
            student=self.student2,
        )

        # Baseline check of submitted answers
        self._check_answer_text(self.assessment1, self.student1, "Some answer text.")
        self._check_answer_text(self.assessment2, self.student1, "Some answer text.")
        self._check_answer_text(self.assessment1, self.student2, None)
        self._check_answer_text(self.assessment2, self.student2, "Some answer text.")

    def _check_answer_text(self, assessment, student, expected_answer_text):
        """
        Checks that the answer text for the given assessment+student
        is as expected.
        """
        answer = get_answer_data(self.course, assessment=assessment, student=student)
        assert answer['answer_text'] == expected_answer_text

    def test_delete_submitted_answers_for_course(self):
        assert delete_submitted_answers(course=self.course) == 3

        self._check_answer_text(self.assessment1, self.student1, None)
        self._check_answer_text(self.assessment2, self.student1, None)
        self._check_answer_text(self.assessment1, self.student2, None)
        self._check_answer_text(self.assessment2, self.student2, None)

    def test_delete_submitted_answers_for_student(self):
        assert delete_submitted_answers(course=self.course, student=self.student1) == 2

        self._check_answer_text(self.assessment1, self.student1, None)
        self._check_answer_text(self.assessment2, self.student1, None)
        self._check_answer_text(self.assessment1, self.student2, None)
        self._check_answer_text(self.assessment2, self.student2, "Some answer text.")

    def test_delete_submitted_answers_for_assessment(self):
        assert delete_submitted_answers(course=self.course, assessment=self.assessment1) == 1

        self._check_answer_text(self.assessment1, self.student1, None)
        self._check_answer_text(self.assessment2, self.student1, "Some answer text.")
        self._check_answer_text(self.assessment1, self.student2, None)
        self._check_answer_text(self.assessment2, self.student2, "Some answer text.")

    def test_delete_submitted_answers_for_assessment_student(self):
        assert delete_submitted_answers(course=self.course, assessment=self.assessment2, student=self.student1) == 1

        self._check_answer_text(self.assessment1, self.student1, "Some answer text.")
        self._check_answer_text(self.assessment2, self.student1, None)
        self._check_answer_text(self.assessment1, self.student2, None)
        self._check_answer_text(self.assessment2, self.student2, "Some answer text.")
