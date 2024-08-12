import logging
from time import sleep

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver

from kinesinlms.course.models import EnrollmentSurveyAnswer, Enrollment
from kinesinlms.course.tests.factories import CourseFactory, EnrollmentSurveyFactory, EnrollmentSurveyQuestionFactory

User = get_user_model()
logger = logging.getLogger(__name__)

TEST_USER_NAME = "test-student"
TEST_USER_PW = "test-student-pw-123"
TEST_USER_EMAIL = "test-student@example.com"


class TestEnrollment(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            cls.selenium = WebDriver()
            cls.selenium.implicitly_wait(10)
        except Exception:
            cls.selenium = None
            # Couldn't load selenium...we're probably running on Heroku
            # TODO Tried using pytest skip statements but couldn't get them to work
            # TODO so just using a simpler mechanism of checking whether class variable is set.
            logger.exception("Can't find Selenium...skipping MySeleniumTests")

        course = CourseFactory(self_paced=True)
        cls.course_base_url = course.course_url
        cls.course = course
        user = User.objects.create_user(username=TEST_USER_NAME,
                                        password=TEST_USER_PW,
                                        email=TEST_USER_EMAIL)
        user.save()

        email_address, created = EmailAddress.objects.get_or_create(user=user,
                                                                    email=TEST_USER_EMAIL)
        email_address.primary = True
        email_address.verified = True
        email_address.save()

        # set up an enrollment survey
        enrollment_question = EnrollmentSurveyQuestionFactory.create()
        cls.enrollment_question = enrollment_question
        enrollment_survey = EnrollmentSurveyFactory.create(course=course)
        enrollment_survey.questions.add(enrollment_question)
        cls.enrollment_survey = enrollment_survey

        cls.user = user

    @classmethod
    def tearDownClass(cls):
        if cls.selenium:
            cls.selenium.quit()
        super(TestEnrollment, cls).tearDownClass()

    def test_enrollment_survey(self):
        if not self.selenium:
            return

        self.assertEqual(0, Enrollment.objects.count())

        # Make student is signed in before continuing...
        self.selenium.get(f"{self.live_server_url}/accounts/login?next=/catalog/TEST/SP/")
        username_input = self.selenium.find_element(By.ID, 'id_login')
        username_input.send_keys(TEST_USER_NAME)
        password_input = self.selenium.find_element(By.ID, 'id_password')
        password_input.send_keys(TEST_USER_PW)
        login_button = self.selenium.find_element(By.ID, 'sign_in_btn')
        login_button.click()
        sleep(2)

        # Find the enrollment button and click it.
        enroll_btn = self.selenium.find_element(By.ID, "enroll_btn")
        enroll_btn.click()

        # Make sure question form is there
        form = self.selenium.find_element(By.ID, "enrollment-survey-form")
        self.assertIsNotNone(form)

        # Select the second to last option, which should correspond to key 'whole-course'
        id_answer_2 = self.selenium.find_element(By.ID, 'id_answer_2')
        id_answer_2.click()
        sleep(1)

        sign_up_button = self.selenium.find_element(By.ID, 'btn-submit-survey')
        sign_up_button.click()

        sleep(3)

        # We should now see the catalog page with the "View Course Button" now showing
        view_course_btn = self.selenium.find_element(By.ID, 'view_course_btn')
        self.assertIsNotNone(view_course_btn)

        # Make sure user was enrolled and the enrollment survey question answer was stored
        enrollment = Enrollment.objects.get(student=self.user,
                                            course=self.course)
        self.assertTrue(enrollment.active)
        expected_value = self.enrollment_question.definition[2]['key']
        enrollment_question_answer = EnrollmentSurveyAnswer.objects.get(enrollment=enrollment)
        self.assertEqual(expected_value, enrollment_question_answer.answer)
