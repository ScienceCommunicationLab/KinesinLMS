import logging
from time import sleep

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver

from kinesinlms.course.tests.factories import CourseFactory

User = get_user_model()
logger = logging.getLogger(__name__)

TEST_USER_NAME = "test-student"
TEST_USER_PW = "test-student-pw-123"
TEST_USER_EMAIL = "test-student@example.com"


class TestLogin(StaticLiveServerTestCase):
    # fixtures = ['test-user-data.json', 'test-products.json']

    @classmethod
    def setUpClass(cls):
        """
        Create a basic course, so we can test logging in then enrolling.
        """
        super().setUpClass()

        course = CourseFactory()
        cls.course_base_url = course.course_url
        cls.course = course
        user = User.objects.create_user(username=TEST_USER_NAME,
                                        password=TEST_USER_PW,
                                        email=TEST_USER_EMAIL)
        user.save()
        EmailAddress.objects.create(user=user,
                                    email=TEST_USER_EMAIL,
                                    primary=True,
                                    verified=True)
        cls.user = user

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
        super(TestLogin, cls).tearDownClass()

    def test_login_and_enroll(self):
        if not self.selenium:
            return
        # Go straight to the 'some course' about page, so we can enroll after logging in...
        self.selenium.get(f"{self.live_server_url}/accounts/login?next=/catalog/TEST/SP/")
        username_input = self.selenium.find_element(By.ID, 'id_login')
        username_input.send_keys(TEST_USER_NAME)
        password_input = self.selenium.find_element(By.ID, 'id_password')
        password_input.send_keys(TEST_USER_PW)
        login_button = self.selenium.find_element(By.ID, 'sign_in_btn')
        login_button.click()
        sleep(2)
        enroll_btn = self.selenium.find_element(By.ID, "enroll_btn")
        enroll_btn.click()
        sleep(5)
        view_course_btn = self.selenium.find_element(By.ID, "view_course_btn")
        self.assertIsNotNone(view_course_btn)
