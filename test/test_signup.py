import logging
import re
from time import sleep

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core import mail
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from kinesinlms.course.models import Enrollment, CohortType
from kinesinlms.course.tests.factories import CourseFactory, CohortFactory
from kinesinlms.course.utils import user_is_enrolled
from kinesinlms.users.models import CareerStageType, GenderType, UserSettings, InviteUser

User = get_user_model()
logger = logging.getLogger(__name__)

TEST_USER_NAME = "Tester McStudent"
TEST_USER_USERNAME = "test_student"
TEST_USER_PW = "blahblah90134"
TEST_USER_EMAIL = "test-student@example.com"
TEST_USER_INFORMAL_NAME = "Tester"
TEST_GENDER_DESCRIPTION = "Test gender description"


class TestSignup(StaticLiveServerTestCase):
    # fixtures = ['test-user-data.json', 'test-products.json']

    @classmethod
    def setUpClass(cls):
        """
        Create a basic course, so we can test logging in then enrolling.
        """
        super().setUpClass()
        cls.selenium = None
        try:
            cls.selenium = WebDriver()
            cls.selenium.implicitly_wait(10)
        except Exception:
            cls.selenium = None
            # Couldn't load selenium...we're probably running on Heroku
            # TODO Tried using pytest skip statements but couldn't get them to work
            # TODO so just using a simpler mechanism of checking whether class variable is set.
            logger.exception("Can't find Selenium...skipping MySeleniumTests")

    @classmethod
    def tearDownClass(cls):
        if cls.selenium:
            cls.selenium.quit()
        super(TestSignup, cls).tearDownClass()

    def setUp(self):

        self.course = CourseFactory.create()
        self.cohort = CohortFactory.create(course=self.course,
                                           type=CohortType.DEFAULT.name,
                                           slug="default-cohort")
        if not self.selenium:
            return
        pass

    def test_signup(self):
        """
        Make sure a user can sign up.
        :return:
        """
        if not self.selenium:
            return

        self.selenium.get(f"{self.live_server_url}/accounts/signup/")

        email_input = self.selenium.find_element(By.ID, 'id_email')
        email_input.send_keys(TEST_USER_EMAIL)

        username_input = self.selenium.find_element(By.ID, 'id_username')
        username_input.send_keys(TEST_USER_USERNAME)

        password1_input = self.selenium.find_element(By.ID, 'id_password1')
        password1_input.send_keys(TEST_USER_PW)
        password1_input = self.selenium.find_element(By.ID, 'id_password2')
        password1_input.send_keys(TEST_USER_PW)

        full_name_input = self.selenium.find_element(By.ID, 'id_name')
        full_name_input.send_keys(TEST_USER_NAME)

        self.selenium.execute_script("window.scrollBy(0, 500);")
        sleep(3)

        informal_name_input = self.selenium.find_element(By.ID, 'id_informal_name')
        informal_name_input.send_keys(TEST_USER_INFORMAL_NAME)

        career_stage_input = self.selenium.find_element(By.ID, 'id_career_stage')
        career_stage_select = Select(career_stage_input)
        career_stage_select.select_by_value(CareerStageType.MASTERS)

        self.selenium.execute_script("window.scrollBy(0, 300);")
        sleep(3)

        year_of_birth_input = self.selenium.find_element(By.ID, 'id_year_of_birth')
        year_of_birth_select = Select(year_of_birth_input)
        year_of_birth_select.select_by_value('1971')

        gender_input = self.selenium.find_element(By.ID, 'id_gender')
        gender_select = Select(gender_input)
        gender_select.select_by_value(GenderType.MALE.name)

        gender_description_input = self.selenium.find_element(By.ID, 'id_gender_description')
        gender_description_input.send_keys(TEST_GENDER_DESCRIPTION)

        self.selenium.execute_script("window.scrollBy(0, 300);")
        sleep(3)

        agree_to_honor_code_input = self.selenium.find_element(By.ID, 'id_agree_to_honor_code')
        agree_to_honor_code_input.click()

        # Enable badges is defaulted to check so leave it checked...
        # enable_badges_elem = self.selenium.find_element(By.ID, 'id_enable_badges')
        # enable_badges_elem.click()

        sign_up_button = self.selenium.find_element(By.ID, 'sign_up_btn')
        sign_up_button.click()

        sleep(3)

        # They should have gotten to the next page, which is the
        # one that asks them to verify their account by clicking
        # link in email...
        body = self.selenium.find_element(By.TAG_NAME, 'body')
        self.assertIn("Verify Your E-mail Address", body.text)

        user = User.objects.get(username=TEST_USER_USERNAME)
        settings: UserSettings = user.get_settings()
        # Make sure settings was created and enable badges was set to True
        self.assertEqual(settings.enable_badges, True)

    def test_signup_for_invite_user(self):
        """
        Make sure that a user marked as an InviteUser
        is enrolled after registration
        """
        if not self.selenium:
            return

        # Sanity check
        self.assertTrue(User.objects.count() == 0)
        self.assertTrue(Enrollment.objects.count() == 0)

        # Create an InviteUser. This would have been created by a
        # staff or CourseEducator as part of the invite-to-enroll workflow.
        InviteUser.objects.create(email=TEST_USER_EMAIL,
                                  cohort=self.cohort)

        # Do registration. This should cause student to be
        # automatically enrolled in course.
        self.selenium.get(f"{self.live_server_url}/accounts/signup/")

        email_input = self.selenium.find_element(By.ID, 'id_email')
        email_input.send_keys(TEST_USER_EMAIL)

        username_input = self.selenium.find_element(By.ID, 'id_username')
        username_input.send_keys(TEST_USER_USERNAME)

        password1_input = self.selenium.find_element(By.ID, 'id_password1')
        password1_input.send_keys(TEST_USER_PW)
        password1_input = self.selenium.find_element(By.ID, 'id_password2')
        password1_input.send_keys(TEST_USER_PW)

        full_name_input = self.selenium.find_element(By.ID, 'id_name')
        full_name_input.send_keys(TEST_USER_NAME)

        self.selenium.execute_script("window.scrollBy(0, 500);")
        sleep(3)

        informal_name_input = self.selenium.find_element(By.ID, 'id_informal_name')
        informal_name_input.send_keys(TEST_USER_INFORMAL_NAME)

        career_stage_input = self.selenium.find_element(By.ID, 'id_career_stage')
        career_stage_select = Select(career_stage_input)
        career_stage_select.select_by_value(CareerStageType.MASTERS)

        self.selenium.execute_script("window.scrollBy(0, 300);")
        sleep(3)

        year_of_birth_input = self.selenium.find_element(By.ID, 'id_year_of_birth')
        year_of_birth_select = Select(year_of_birth_input)
        year_of_birth_select.select_by_value('1971')

        gender_input = self.selenium.find_element(By.ID, 'id_gender')
        gender_select = Select(gender_input)
        gender_select.select_by_value(GenderType.MALE.name)

        gender_description_input = self.selenium.find_element(By.ID, 'id_gender_description')
        gender_description_input.send_keys(TEST_GENDER_DESCRIPTION)

        self.selenium.execute_script("window.scrollBy(0, 300);")
        sleep(3)

        agree_to_honor_code_input = self.selenium.find_element(By.ID, 'id_agree_to_honor_code')
        agree_to_honor_code_input.click()

        # Enable badges is defaulted to check so leave it checked...
        # enable_badges_elem = self.selenium.find_element(By.ID, 'id_enable_badges')
        # enable_badges_elem.click()

        sign_up_button = self.selenium.find_element(By.ID, 'sign_up_btn')
        sign_up_button.click()

        sleep(3)

        # They should have gotten to the next page, which is the
        # one that asks them to verify their account by clicking
        # link in email...
        body = self.selenium.find_element(By.TAG_NAME, 'body')
        self.assertIn("Verify Your E-mail Address", body.text)

        # Find confirmation link in email and click it...
        mail_body = mail.outbox[0].body
        confirmation_url = extract_confirmation_url(mail_body)
        self.selenium.get(confirmation_url)

        button = WebDriverWait(self.selenium, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "btn-primary"))
        )
        # Click the button
        button.click()
        sleep(2)

        # Should now be at email validated screen. We don't
        # have to log in again, just prove that user is now enrolled in course.

        user = User.objects.get(username=TEST_USER_USERNAME)

        # Make sure user was enrolled in target course
        is_enrolled = user_is_enrolled(user=user, course=self.course)
        self.assertTrue(is_enrolled)


def extract_confirmation_url(email_body):
    pattern = r'http[s]?://\S+'
    match = re.search(pattern, email_body)
    if match:
        return match.group(0)
    else:
        return None
