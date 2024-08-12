import logging

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver

from kinesinlms.course.models import Enrollment, CourseUnit
from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.learning_library.constants import BlockType
from kinesinlms.learning_library.models import UnitBlock
from kinesinlms.learning_library.tests.factories import BlockFactory
from kinesinlms.sits.tests.factories import TabletoolFactory

User = get_user_model()
logger = logging.getLogger(__name__)

TEST_USER_NAME = "test-student"
TEST_USER_PW = "test-student-pw-123"
TEST_USER_EMAIL = "test-student@example.com"


class TestTabletool(StaticLiveServerTestCase):

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

        course = CourseFactory.create()

        course_unit_1 = CourseUnit.objects.get(slug="course_unit_1")
        tabletool_sit_block = BlockFactory(type=BlockType.SIMPLE_INTERACTIVE_TOOL.name)
        tabletool_sit = TabletoolFactory.create(block=tabletool_sit_block)
        UnitBlock.objects.create(
            course_unit=course_unit_1,
            block=tabletool_sit_block,
            block_order=5
        )
        cls.tabletool_sit = tabletool_sit

        # Make sure course has a Tabletool assignment

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

        # Make sure student is enrolled
        enrollment = Enrollment.objects.create(course=course,
                                               student=user,
                                               active=True)
        cls.enrollment = enrollment

    @classmethod
    def tearDownClass(cls):
        if cls.selenium:
            cls.selenium.quit()
        super(TestTabletool, cls).tearDownClass()

    def test_tabletool(self):
        """
        Test the TABLETOOL Simple Interactive Tool.
        """

        # Make student is signed in before continuing...
        self.selenium.get(f"{self.live_server_url}/accounts/login?next=/catalog/TEST/SP/")
        username_input = self.selenium.find_element(By.ID, 'id_login')
        username_input.send_keys(TEST_USER_NAME)
        password_input = self.selenium.find_element(By.ID, 'id_password')
        password_input.send_keys(TEST_USER_PW)
        login_button = self.selenium.find_element(By.ID, 'sign_in_btn')
        login_button.click()
        self.selenium.implicitly_wait(5)

        # Navigate to the unit with our Tabletool block.
        self.selenium.get(f"{self.live_server_url}/courses/TEST/SP/content/"
                          f"basic_module/basic_section_1/course_unit_1/")
        self.selenium.implicitly_wait(5)

        # Make sure some expected elements are there
        expected_wrapper_div_id = f"simple-interactive-tool-{self.tabletool_sit.id}"
        tabletool_div = self.selenium.find_element(By.ID, expected_wrapper_div_id)
        self.selenium.execute_script("arguments[0].scrollIntoView();", tabletool_div)
        self.selenium.implicitly_wait(15)

        instructions_div = self.selenium.find_element(By.ID, f"sit-instructions-accordian-{self.tabletool_sit.id}")
        self.assertIn("Here are some instructions.", instructions_div.text)
