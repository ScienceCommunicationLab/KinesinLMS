import logging

from django.contrib.auth import get_user_model
from django.forms.models import model_to_dict
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from kinesinlms.assessments.tests.factories import (
    DoneIndicatorAssessmentFactory,
    LongFormAssessmentFactory,
    MultipleChoiceAssessmentFactory,
    PollAssessmentFactory,
)
from kinesinlms.course.tests.factories import BlockFactory, CourseFactory
from kinesinlms.learning_library.constants import BlockType, AssessmentType
from kinesinlms.learning_library.models import UnitBlock

logger = logging.getLogger(__name__)

TRACKING_API_ENDPOINT = '/api/bookmarks/'


class TestComposerBlockCRUD(TestCase):
    """
    Test the views that allow blocks to be
    created, edited and deleted.
    """

    def setUp(self):
        course = CourseFactory()
        self.course_base_url = course.course_url
        self.course = course

        User = get_user_model()
        self.admin_user = User.objects.create(username="daniel",
                                              is_staff=True,
                                              is_superuser=True)

    def test_add_html_block(self):
        """
        Add an HTML block to the first unit and then make sure it's there.
        """

        module_node = self.course.course_root_node.get_children()[0]
        section_node = module_node.get_children()[0]
        unit_node = section_node.get_children()[0]
        course_unit = unit_node.unit

        block_type = BlockType.HTML_CONTENT.name

        before_add_count = course_unit.contents.count()

        self.client.force_login(self.admin_user)
        index_url = reverse('composer:add_course_unit_block_type_hx', kwargs={
            'course_id': self.course.id,
            'course_unit_id': course_unit.id,
            'module_node_id': module_node.id,
            'section_node_id': section_node.id,
            'unit_node_id': unit_node.id,
            'block_type': block_type
        })

        response = self.client.post(index_url)
        # The response should be a redirect to the edit page for the new block.
        self.assertEqual(302, response.status_code)
        self.assertEqual("edit", response.url.split("/")[-2])
        after_add_count = course_unit.contents.count()
        self.assertTrue(after_add_count == before_add_count + 1)

    def test_add_video_block(self):
        """
        Add a VIDEO block to the first unit and then make sure it's there.
        """

        module_node = self.course.course_root_node.get_children()[0]
        section_node = module_node.get_children()[0]
        unit_node = section_node.get_children()[0]
        course_unit = unit_node.unit

        block_type = BlockType.VIDEO.name

        before_add_count = course_unit.contents.count()

        self.client.force_login(self.admin_user)
        index_url = reverse('composer:add_course_unit_block_type_hx', kwargs={
            'course_id': self.course.id,
            'course_unit_id': course_unit.id,
            'module_node_id': module_node.id,
            'section_node_id': section_node.id,
            'unit_node_id': unit_node.id,
            'block_type': block_type
        })

        response = self.client.post(index_url)
        # The response should be a redirect to the edit page for the new block.
        self.assertEqual(302, response.status_code)
        self.assertEqual("edit", response.url.split("/")[-2])
        after_add_count = course_unit.contents.count()
        self.assertTrue(after_add_count == before_add_count + 1)

    def test_add_long_form_text_assessment_block(self):
        """
        Add an ASSESSMENT block of type LONG_FORM_TEXT
        to the first unit and then make sure it's there.
        """

        module_node = self.course.course_root_node.get_children()[0]
        section_node = module_node.get_children()[0]
        unit_node = section_node.get_children()[0]
        course_unit = unit_node.unit

        block_type = BlockType.ASSESSMENT.name
        block_subtype = AssessmentType.LONG_FORM_TEXT.name

        before_add_count = course_unit.contents.count()

        self.client.force_login(self.admin_user)
        index_url = reverse('composer:add_course_unit_block_type_subtype_hx', kwargs={
            'course_id': self.course.id,
            'module_node_id': module_node.id,
            'section_node_id': section_node.id,
            'unit_node_id': unit_node.id,
            'course_unit_id': course_unit.id,
            'block_type': block_type,
            'block_subtype': block_subtype
        })

        response = self.client.post(index_url)
        # The response should be a redirect to the edit page for the new block.
        self.assertEqual(302, response.status_code)
        self.assertEqual("edit", response.url.split("/")[-2])
        after_add_count = course_unit.contents.count()
        self.assertTrue(after_add_count == before_add_count + 1)

    def test_add_multiple_choice_text_assessment_block(self):
        """
        Add an ASSESSMENT block of type MULTIPLE_CHOICE
        to the first unit and then make sure it's there.
        """

        module_node = self.course.course_root_node.get_children()[0]
        section_node = module_node.get_children()[0]
        unit_node = section_node.get_children()[0]
        course_unit = unit_node.unit

        block_type = BlockType.ASSESSMENT.name
        block_subtype = AssessmentType.MULTIPLE_CHOICE.name

        before_add_count = course_unit.contents.count()

        self.client.force_login(self.admin_user)
        index_url = reverse('composer:add_course_unit_block_type_subtype_hx', kwargs={
            'course_id': self.course.id,
            'module_node_id': module_node.id,
            'section_node_id': section_node.id,
            'unit_node_id': unit_node.id,
            'course_unit_id': course_unit.id,
            'block_type': block_type,
            'block_subtype': block_subtype
        })

        response = self.client.post(index_url)
        # The response should be a redirect to the edit page for the new block.
        self.assertEqual(302, response.status_code)
        self.assertEqual("edit", response.url.split("/")[-2])
        after_add_count = course_unit.contents.count()
        self.assertTrue(after_add_count == before_add_count + 1)

    def test_add_poll_text_assessment_block(self):
        """
        Add an ASSESSMENT block of type POLL
        to the first unit and then make sure it's there.
        """

        module_node = self.course.course_root_node.get_children()[0]
        section_node = module_node.get_children()[0]
        unit_node = section_node.get_children()[0]
        course_unit = unit_node.unit

        block_type = BlockType.ASSESSMENT.name
        block_subtype = AssessmentType.POLL.name

        before_add_count = course_unit.contents.count()

        self.client.force_login(self.admin_user)
        index_url = reverse('composer:add_course_unit_block_type_subtype_hx', kwargs={
            'course_id': self.course.id,
            'module_node_id': module_node.id,
            'section_node_id': section_node.id,
            'unit_node_id': unit_node.id,
            'course_unit_id': course_unit.id,
            'block_type': block_type,
            'block_subtype': block_subtype
        })

        response = self.client.post(index_url)
        # The response should be a redirect to the edit page for the new block.
        self.assertEqual(302, response.status_code)
        self.assertEqual("edit", response.url.split("/")[-2])
        after_add_count = course_unit.contents.count()
        self.assertTrue(after_add_count == before_add_count + 1)

    def _create_assessment(self, AssessmentFactory):
        """
        Create an Assessment using the given AssessmentFactory,
        and insert it into the current course.

        Returns the assessment and the URL used to edit this assessment block.
        """
        module_node = self.course.course_root_node.get_children()[0]
        section_node = module_node.get_children()[0]
        unit_node = section_node.get_children()[0]
        course_unit = unit_node.unit

        assessment_block = BlockFactory(type=BlockType.ASSESSMENT.name)
        assessment = AssessmentFactory(block=assessment_block)
        UnitBlock.objects.create(
            course_unit=course_unit,
            block=assessment_block,
            block_order=1
        )
        assessment_block.save()

        edit_url = reverse('composer:blocks:edit_block_panel_set_hx', kwargs={
            'course_id': self.course.id,
            'module_node_id': module_node.id,
            'section_node_id': section_node.id,
            'unit_node_id': unit_node.id,
            'course_unit_id': course_unit.id,
            'pk': assessment_block.id
        })

        return assessment, edit_url

    def _assemble_post_data(self, assessment, changed_data):
        """
        Assemble the POST data from the assessment's current data + the changed data
        """
        post_data = model_to_dict(assessment)
        post_data.update(changed_data)
        for field in post_data:
            if post_data[field] is None:
                post_data[field] = ""

        return post_data

    @patch('kinesinlms.composer.blocks.panels.forms.rescore_assessment_milestone_progress.apply_async')
    def _test_rescore_assessment_block(self, AssessmentFactory, changed_data, mock_rescore):
        """
        Helper method for testing when "rescore assessments" is triggerered
        by Composer's Assessment edit forms.
        """
        assessment, edit_url = self._create_assessment(AssessmentFactory)
        self.client.force_login(self.admin_user)

        # Post no changes -- rescore should not be triggered
        response = self.client.post(edit_url)
        self.assertEqual(200, response.status_code)
        assert not mock_rescore.called, 'Rescore should not be triggered if no changes were made.'

        # Post grading-related changes -- rescore should be triggered
        post_data = self._assemble_post_data(assessment, changed_data)
        response = self.client.post(edit_url, data=post_data)
        self.assertEqual(200, response.status_code)
        mock_rescore.assert_called_once_with(
            args=[],
            kwargs={
                "course_id": self.course.id,
                "assessment_id": assessment.id,
            }
        )

    def test_rescore_long_form_assessment_block(self):
        self._test_rescore_assessment_block(LongFormAssessmentFactory,
                                            {'max_score': 5})

    def test_rescore_done_assessment_block(self):
        self._test_rescore_assessment_block(DoneIndicatorAssessmentFactory,
                                            {'done_indicator_label': 'this field is required',
                                             'graded': False})

    def test_rescore_multiple_choice_assessment(self):
        # Multiple-choice forms are complicated, so we have to send a lot of fields.
        self._test_rescore_assessment_block(
            MultipleChoiceAssessmentFactory,
            {
                            'join_type': "AND",
                            'question-definition-TOTAL_FORMS': "4",
                            'question-definition-INITIAL_FORMS': "4",
                            'question-definition-MIN_NUM_FORMS': "1",
                            'question-definition-MAX_NUM_FORMS': "20",
                            'question-definition-0-choice_key': "A",
                            'question-definition-0-text': "Walther Flemming",
                            'question-definition-1-choice_key': "B",
                            'question-definition-1-text': "Robert Hooke",
                            'question-definition-1-correct': "on",
                            'question-definition-2-choice_key': "C",
                            'question-definition-2-text': "Isaac Newton",
                            'question-definition-3-choice_key': "D",
                            'question-definition-3-text': "Antonie van Leeuvenhoek",
                            'question-definition-2-correct': "on",  # <-- here is the change
                        })

    def test_rescore_poll_assessment(self):
        # Poll forms are complicated, so we have to send a lot of fields.
        self._test_rescore_assessment_block(
            PollAssessmentFactory,
            {
                'question-definition-TOTAL_FORMS': "4",
                'question-definition-INITIAL_FORMS': "4",
                'question-definition-MIN_NUM_FORMS': "1",
                'question-definition-MAX_NUM_FORMS': "20",
                'question-definition-0-choice_key': "A",
                'question-definition-0-text': "Walther Flemming",
                'question-definition-1-choice_key': "Bb",  # <-- here is the change
                'question-definition-1-text': "Robert Hooke",
                'question-definition-2-choice_key': "C",
                'question-definition-2-text': "Isaac Newton",
                'question-definition-3-choice_key': "D",
                'question-definition-3-text': "Antonie van Leeuvenhoek",
            })
