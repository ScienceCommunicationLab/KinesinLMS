import logging
from time import sleep

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver

from kinesinlms.course.models import CourseStaffRole, CourseStaff
from kinesinlms.course.tests.factories import CourseFactory, EnrollmentFactory
from kinesinlms.users.tests.factories import EducatorFactory, UserFactory
from kinesinlms.users.utils import create_default_groups

User = get_user_model()
logger = logging.getLogger(__name__)

TEST_USER_USERNAME = "test-student"
TEST_USER_PW = "student-123"
TEST_USER_EMAIL = "test-student@example.com"

COURSE_EDUCATOR_USERNAME = "test-course-educator"
COURSE_EDUCATOR_PW = "ce-123"
COURSE_EDUCATOR_EMAIL = "test-course-educator@example.com"


class TestCourseAdmin(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_default_groups()
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
        super(TestCourseAdmin, cls).tearDownClass()

    def test_course_educator_can_see_course_admin_tabs(self):
        if not self.selenium:
            return

        course = CourseFactory(slug="TEST", run="run1")

        course_educator = EducatorFactory.create(
            username=COURSE_EDUCATOR_USERNAME,
            password=COURSE_EDUCATOR_PW,
            email=COURSE_EDUCATOR_EMAIL,
        )

        EmailAddress.objects.create(
            user=course_educator,
            email=COURSE_EDUCATOR_EMAIL,
            primary=True,
            verified=True,
        )

        CourseStaff.objects.create(
            course=course,
            user=course_educator,
            role=CourseStaffRole.EDUCATOR.name,
        )

        EnrollmentFactory(course=course, student=course_educator, active=True)

        # Make sure course educator is signed in before continuing...
        self.selenium.get(
            f"{self.live_server_url}/accounts/login?next=/courses/{course.slug}/{course.run}/course_admin/analytics/"
        )
        sleep(2)

        username_input = self.selenium.find_element(By.ID, "id_login")
        username_input.send_keys(COURSE_EDUCATOR_EMAIL)
        password_input = self.selenium.find_element(By.ID, "id_password")
        password_input.send_keys(COURSE_EDUCATOR_PW)
        login_button = self.selenium.find_element(By.ID, "sign_in_btn")
        login_button.click()
        sleep(2)

        # Make sure we can see the course admin tab
        course_admin_tab = self.selenium.find_element(By.ID, "course-admin-nav-item")
        self.assertIsNotNone(course_admin_tab)

        # Make sure course educator can see Analytics and Cohorts tabs
        course_analytics_tab_elem = self.selenium.find_element(
            By.ID, "tab-course-analytics"
        )
        self.assertIsNotNone(course_analytics_tab_elem)
        course_cohorts_tab_elem = self.selenium.find_element(
            By.ID, "tab-course-cohorts"
        )
        self.assertIsNotNone(course_cohorts_tab_elem)

        # Make sure course educator *cannot* see cohorts and email invites, that's for super and staff only...
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.ID, "tab-course-enrollment")

    def test_student_cannot_see_course_admin_tabs(self):
        if not self.selenium:
            return

        course = CourseFactory(slug="TEST", run="run2")

        # Make sure user actually exists
        user = UserFactory.create(
            username=TEST_USER_USERNAME, password=TEST_USER_PW, email=TEST_USER_EMAIL
        )

        EmailAddress.objects.create(
            user=user, email=TEST_USER_EMAIL, primary=True, verified=True
        )

        # Make sure student is enrolled
        EnrollmentFactory.create(course=course, student=user, active=True)

        # Make sure student is signed in before continuing...
        self.selenium.get(
            f"{self.live_server_url}/accounts/login?next=/courses/{course.slug}/{course.run}/"
        )
        username_input = self.selenium.find_element(By.ID, "id_login")
        username_input.send_keys(TEST_USER_EMAIL)
        password_input = self.selenium.find_element(By.ID, "id_password")
        password_input.send_keys(TEST_USER_PW)
        login_button = self.selenium.find_element(By.ID, "sign_in_btn")
        login_button.click()
        sleep(4)

        # Make sure we cannot see the course admin tab
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.ID, "course-admin-nav-item")
