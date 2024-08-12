import logging
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.survey.constants import SurveyType
from kinesinlms.survey.models import Survey, SurveyCompletion, SurveyProviderType
from kinesinlms.survey.tests.factories import SurveyFactory, SurveyProviderFactory
from kinesinlms.users.tests.factories import UserFactory

logger = logging.getLogger(__name__)

User = get_user_model()


class TestSurveyCallbackEndpoint(TestCase):

    def setUp(self):
        course = CourseFactory(slug="PYSJ", run="SP")
        self.course = course
        self.enrolled_user: User = UserFactory.create(username="enrolled-user",
                                                      email="enrolled_user@example.com")

        self.survey_provider = SurveyProviderFactory.create(datacenter_id="some-datacenter-id",
                                                            type=SurveyProviderType.QUALTRICS.name,
                                                            callback_secret="some-callback-secret")

        self.post_course_survey: Survey = SurveyFactory.create(course=self.course,
                                                               provider=self.survey_provider,
                                                               survey_id="some-test-survey-1",
                                                               type=SurveyType.POST_COURSE.name,
                                                               send_reminder_email=True,
                                                               days_delay=2,
                                                               url="example.com/some/survey/url.html")

        self.valid_callback_data = {
            'survey_id': self.post_course_survey.survey_id,
            'uid': self.enrolled_user.anon_username,
            'secret': 'some-callback-secret',
            'response_id': 1234
        }

    def test_missing_param(self):
        required_params = ['survey_id', 'uid', 'secret', 'response_id']
        for param in required_params:
            callback_data = self.valid_callback_data.copy()
            callback_data.pop(param)
            callback_url = reverse("surveys:student_survey_complete_callback")
            response = self.client.post(callback_url,
                                        data=callback_data,
                                        content_type='application/json')
            self.assertEqual(400, response.status_code)

    def test_incorrect_secret(self):
        callback_data = self.valid_callback_data.copy()
        callback_data['secret'] = 'incorrect-secret'
        callback_url = reverse("surveys:student_survey_complete_callback")
        response = self.client.post(callback_url,
                                    data=callback_data,
                                    content_type='application/json')
        self.assertEqual(404, response.status_code)

    def test_invalid_survey_uid(self):
        callback_data = self.valid_callback_data.copy()
        callback_data['survey_id'] = 'invalid-survey-id'
        callback_url = reverse("surveys:student_survey_complete_callback")
        response = self.client.post(callback_url,
                                    data=callback_data,
                                    content_type='application/json')
        self.assertEqual(404, response.status_code)

    def test_invalid_uid(self):
        callback_data = self.valid_callback_data.copy()
        callback_data['uid'] = uuid.uuid4()
        callback_url = reverse("surveys:student_survey_complete_callback")
        response = self.client.post(callback_url,
                                    data=callback_data,
                                    content_type='application/json')
        self.assertEqual(404, response.status_code)

    def test_valid_survey_callback(self):
        """
        Pretend to be an external survey provider hitting our callback view.
        """
        callback_data = self.valid_callback_data.copy()
        callback_url = reverse("surveys:student_survey_complete_callback")
        response = self.client.post(callback_url,
                                    data=callback_data,
                                    content_type='application/json')
        self.assertEqual(200, response.status_code)
        survey_completion = SurveyCompletion.objects.get(user=self.enrolled_user,
                                                         survey=self.post_course_survey)
        self.assertEqual(survey_completion.times_completed, 1)
