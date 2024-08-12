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


class TestThirdModuleUnreleasedClass(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        """
        Do more extensive testing of a course with a varied release schedule.
        """
        super(TestThirdModuleUnreleasedClass, cls).setUpClass()

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
        super(TestThirdModuleUnreleasedClass, self).setUp()
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
        super(TestThirdModuleUnreleasedClass, cls).tearDownClass()

    def test_cannot_access_unreleased_first_module(self):

        if not self.selenium:
            return

        module_1: CourseNode = CourseNode.objects.get(slug='module_1')
        module_1.release_datetime = now() + timedelta(days=1)
        module_1.save()

        module_2: CourseNode = CourseNode.objects.get(slug='module_2')
        module_2.release_datetime = now() + timedelta(days=-1)
        module_2.save()

        module_3: CourseNode = CourseNode.objects.get(slug='module_3')
        module_3.release_datetime = now() + timedelta(days=-1)
        module_3.save()

        # Make student is signed in before continuing...
        self.selenium.get(f"{self.live_server_url}/accounts/login?next=/catalog/TEST/R1/")
        username_input = self.selenium.find_element(By.ID, 'id_login')
        username_input.send_keys(TEST_USER_NAME)
        password_input = self.selenium.find_element(By.ID, 'id_password')
        password_input.send_keys(TEST_USER_PW)
        login_button = self.selenium.find_element(By.ID, 'sign_in_btn')
        login_button.click()
        sleep(1)

        # The first module is not released, so going to a unit in that module
        # directly should give a 404
        first_unit_url = f"{self.live_server_url}{self.course_content_base_url}" \
                         f"module_1/section_1/course_unit_1/"
        self.selenium.get(first_unit_url)
        sleep(1)
        e = self.selenium.find_element(By.XPATH, "//*[contains(.,'404 Error: Page not found')]")
        self.assertIsNotNone(e)

        # Make sure module 2 is available and 2 and 3 are shown as available in the nav
        first_unit_url = f"{self.live_server_url}{self.course_content_base_url}" \
                         f"module_2/section_3/"
        self.selenium.get(first_unit_url)
        sleep(1)

        e = self.selenium.find_element(By.XPATH, "//*[contains(.,'Video for Unit 5')]")
        self.assertIsNotNone(e)

        module_2_id = CourseNode.objects.get(slug="module_2").id
        expected_id = f"nav-module-{module_2_id}"
        e = self.selenium.find_element(By.ID, expected_id)
        self.assertIsNotNone(e)
        module_3_id = CourseNode.objects.get(slug="module_3").id
        expected_id = f"nav-module-{module_3_id}"
        e = self.selenium.find_element(By.ID, expected_id)
        self.assertIsNotNone(e)

        # make sure 1 is not yet released
        module_1_id = CourseNode.objects.get(slug="module_1").id
        expected_id = f"nav-node-{module_1_id}-release-date-info"
        e = self.selenium.find_element(By.ID, expected_id)
        self.assertIsNotNone(e)

    def test_cannot_access_unreleased_second_module(self):

        if not self.selenium:
            return

        module_2: CourseNode = CourseNode.objects.get(slug='module_2')
        module_2.release_datetime = now() + timedelta(days=1)
        module_2.save()

        module_3: CourseNode = CourseNode.objects.get(slug='module_3')
        module_3.release_datetime = now() + timedelta(days=-1)
        module_3.save()

        # Make student is signed in before continuing...
        self.selenium.get(f"{self.live_server_url}/accounts/login?next=/catalog/TEST/R1/")
        username_input = self.selenium.find_element(By.ID, 'id_login')
        username_input.send_keys(TEST_USER_NAME)
        password_input = self.selenium.find_element(By.ID, 'id_password')
        password_input.send_keys(TEST_USER_PW)
        login_button = self.selenium.find_element(By.ID, 'sign_in_btn')
        login_button.click()
        sleep(1)

        # Make sure we can get the first page, and on that page
        # the navigation shows the correct message for Module 3 under the navigation.
        first_unit_url = f"{self.live_server_url}{self.course_content_base_url}" \
                         f"module_1/section_1/course_unit_1/"
        self.selenium.get(first_unit_url)

        sleep(1)

        # The nav will give
        # - an id like 'nav-module-{id}' to a published module node
        # - an id like 'nav-section-{id}' to a published section node
        # - an id like 'node-{id}-release-date-info' to the div that holds
        #   the release information. So if we find this we know the nav is showing the right info.

        # Make sure 1 and 3 are available
        module_1_id = CourseNode.objects.get(slug="module_1").id
        expected_id = f"nav-module-{module_1_id}"
        e = self.selenium.find_element(By.ID, expected_id)
        self.assertIsNotNone(e)
        module_3_id = CourseNode.objects.get(slug="module_3").id
        expected_id = f"nav-module-{module_3_id}"
        e = self.selenium.find_element(By.ID, expected_id)
        self.assertIsNotNone(e)
        # make sure 2 is not yet released
        module_2_id = CourseNode.objects.get(slug="module_2").id
        expected_id = f"nav-node-{module_2_id}-release-date-info"
        e = self.selenium.find_element(By.ID, expected_id)
        self.assertIsNotNone(e)

    def test_cannot_access_unreleased_third_module(self):
        """
        The course generated by TimedCourseFactory should have
        a third module that is unreleased. Make sure the
        nav is in the right state and the app responds accordingly.
        """
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
        sleep(1)

        # Make sure we can get the first page, and on that page
        # the navigation shows the correct message for Module 3 under the navigation.
        first_unit_url = f"{self.live_server_url}{self.course_content_base_url}" \
                         f"module_1/section_1/course_unit_1/"
        self.selenium.get(first_unit_url)

        sleep(1)

        # The nav will give
        # - an id like 'nav-module-{id}' to a published module node
        # - an id like 'nav-section-{id}' to a published section node
        # - an id like 'node-{id}-release-date-info' to the div that holds
        #   the release information. So if we find this we know the nav is showing the right info.

        # Make sure 1 and 2 are available
        module_1_id = CourseNode.objects.get(slug="module_1").id
        expected_id = f"nav-module-{module_1_id}"
        e = self.selenium.find_element(By.ID, expected_id)
        self.assertIsNotNone(e)
        module_2_id = CourseNode.objects.get(slug="module_2").id
        expected_id = f"nav-module-{module_2_id}"
        e = self.selenium.find_element(By.ID, expected_id)
        self.assertIsNotNone(e)
        # make sure 3 is not yet released
        module_3_id = CourseNode.objects.get(slug="module_3").id
        expected_id = f"nav-node-{module_3_id}-release-date-info"
        e = self.selenium.find_element(By.ID, expected_id)
        self.assertIsNotNone(e)

    def test_cannot_access_unreleased_second_section(self):

        if not self.selenium:
            return

        section_2: CourseNode = CourseNode.objects.get(slug='section_2')
        section_2.release_datetime = now() + timedelta(days=10)
        section_2.save()

        # Make student is signed in before continuing...
        self.selenium.get(f"{self.live_server_url}/accounts/login?next=/catalog/TEST/R1/")
        username_input = self.selenium.find_element(By.ID, 'id_login')
        username_input.send_keys(TEST_USER_NAME)
        password_input = self.selenium.find_element(By.ID, 'id_password')
        password_input.send_keys(TEST_USER_PW)
        login_button = self.selenium.find_element(By.ID, 'sign_in_btn')
        login_button.click()
        sleep(1)

        # Make sure we can get the first page...
        first_unit_url = f"{self.live_server_url}{self.course_content_base_url}" \
                         f"module_1/section_1/course_unit_1/"
        self.selenium.get(first_unit_url)
        sleep(1)
        # and that section 2 is marked as not yet released in the nav...
        expected_id = f"nav-node-{section_2.id}-release-date-info"
        e = self.selenium.find_element(By.ID, expected_id)
        self.assertIsNotNone(e)

        # You should *not* be able to load up section_2 by going to
        # a URL terminating with that section...
        section_2_url = f"{self.live_server_url}{self.course_content_base_url}" \
                        f"module_1/section_2/"
        self.selenium.get(section_2_url)
        sleep(1)
        # ...you should get a 404...
        e = self.selenium.find_element(By.XPATH, "//*[contains(.,'404 Error: Page not found')]")
        self.assertIsNotNone(e)

        # But section 3 should be available via the URL terminating with the section...
        section_3_url = f"{self.live_server_url}{self.course_content_base_url}" \
                        f"module_2/section_3/"
        self.selenium.get(section_3_url)
        sleep(1)
        e = self.selenium.find_element(By.XPATH, "//*[contains(.,'Video for Unit 5')]")
        self.assertIsNotNone(e)

