import logging
from datetime import timedelta
from time import sleep

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.utils.timezone import now
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver

from kinesinlms.catalog.tests.factories import CourseCatalogDescriptionFactory
from kinesinlms.course.constants import NodeType
from kinesinlms.course.models import Enrollment, CourseNode
from kinesinlms.course.tests.factories import TimedCourseFactory

User = get_user_model()
logger = logging.getLogger(__name__)

TEST_USER_NAME = "test-student"
TEST_USER_PW = "test-student-pw-123"
TEST_USER_EMAIL = "test-student@example.com"


class TestCourseAccess(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        """
        Create a basic course and user so that we can test course access.
        """
        super(TestCourseAccess, cls).setUpClass()

        try:
            cls.selenium = WebDriver()
            cls.selenium.implicitly_wait(10)
        except Exception:
            cls.selenium = None
            # Couldn't load selenium...we're probably running on Heroku
            # TODO Tried using pytest skip statements but couldn't get them to work
            # TODO so just using a simpler mechanism of checking whether class variable is set.
            logger.exception("Can't find Selenium...skipping MySeleniumTests")

    def setUp(self):
        super(TestCourseAccess, self).setUp()
        catalog_description = CourseCatalogDescriptionFactory()
        self.catalog_description = catalog_description

        course = TimedCourseFactory(catalog_description=catalog_description)
        course.save()
        self.course_base_url = course.course_url
        self.course = course

        # Add a student
        user = User.objects.create_user(username=TEST_USER_NAME,
                                        password=TEST_USER_PW,
                                        email=TEST_USER_EMAIL)
        user.save()
        EmailAddress.objects.create(user=user,
                                    email=TEST_USER_EMAIL,
                                    primary=True,
                                    verified=True)
        self.user = user

        # Make sure student is enrolled
        enrollment = Enrollment.objects.create(course=course,
                                               student=user,
                                               active=True)
        self.enrollment = enrollment

        self.course_content_base_url = "/courses/TEST/R1/content/"

    @classmethod
    def tearDownClass(cls):
        if cls.selenium:
            cls.selenium.quit()
        super(TestCourseAccess, cls).tearDownClass()

    def test_cannot_access_unreleased_course_unit_in_a_released_course(self):

        if not self.selenium:
            return

        # Make student is signed in before continuing...
        self.selenium.get(f"{self.live_server_url}/accounts/login?next=/catalog/TEST/R1/")
        username_input = self.selenium.find_element(By.ID, 'id_login')
        username_input.send_keys(TEST_USER_NAME)
        password_input = self.selenium.find_element(By.ID, 'id_password')
        password_input.send_keys(TEST_USER_PW)
        login_button = self.selenium.find_element(By.ID, 'sign_in_btn')
        login_button.click()
        sleep(2)

        # Course started yesterday
        self.course.start_date = now() - timedelta(1)
        self.course.save()
        # But the first unit is not yet available...so we should see something like
        # 'content not available' on that page
        first_unit_node: CourseNode = CourseNode.objects.filter(type=NodeType.UNIT.name).first()
        first_unit_node.release_datetime = now() + timedelta(1)
        first_unit_node.save()

        # Go to first unit page...page should have 'Unit content is unavailable.' in it.
        first_unit_url = f"{self.live_server_url}{self.course_content_base_url}" \
                         f"module_1/section_1/course_unit_1/"
        self.selenium.get(first_unit_url)

        sleep(3)

        e = self.selenium.find_element(By.XPATH, "//*[contains(.,'This unit has not been released yet.')]")

        self.assertIsNotNone(e)

    def test_can_access_unit_in_released_course(self):

        if not self.selenium:
            return

        self.course.start_date = now() - timedelta(1)
        self.course.save()

        first_unit_url = f"{self.live_server_url}{self.course_content_base_url}" \
                         f"module_1/section_1/course_unit_1/"

        # Make student is signed in before continuing...
        self.selenium.get(f"{self.live_server_url}/accounts/login?next=/catalog/TEST/R1/")
        username_input = self.selenium.find_element(By.ID, 'id_login')
        username_input.send_keys(TEST_USER_NAME)
        password_input = self.selenium.find_element(By.ID, 'id_password')
        password_input.send_keys(TEST_USER_PW)
        login_button = self.selenium.find_element(By.ID, 'sign_in_btn')
        login_button.click()
        sleep(2)

        # Go to first unit page...should show 'course not available' page.
        self.selenium.get(first_unit_url)

        sleep(2)

        e = self.selenium.find_element(By.CLASS_NAME, "block-display-name")
        self.assertEqual('Video for Unit 1', e.text)

    def test_cannot_access_course_that_is_not_yet_released(self):

        if not self.selenium:
            return

        self.course.start_date = now() + timedelta(1)
        self.course.save()

        first_unit_url = f"{self.live_server_url}{self.course_content_base_url}" \
                         f"module_1/section_1/course_unit_1/"

        # Make student is signed in before continuing...
        self.selenium.get(f"{self.live_server_url}/accounts/login?next=/catalog/TEST/R1/")
        username_input = self.selenium.find_element(By.ID, 'id_login')
        username_input.send_keys(TEST_USER_NAME)
        password_input = self.selenium.find_element(By.ID, 'id_password')
        password_input.send_keys(TEST_USER_PW)
        login_button = self.selenium.find_element(By.ID, 'sign_in_btn')
        login_button.click()
        sleep(2)

        # Go to first unit page...should show 'course not available' page.
        self.selenium.get(first_unit_url)

        sleep(2)

        e = self.selenium.find_element(By.CLASS_NAME, "access-denied-msg")
        self.assertIsNotNone(e)
