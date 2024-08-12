import logging
from time import sleep

from allauth.account.models import EmailAddress
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver

from kinesinlms.course.constants import MilestoneType
from kinesinlms.course.tests.factories import CourseFactory, EnrollmentFactory, MilestoneFactory
from kinesinlms.users.tests.factories import UserFactory
from kinesinlms.learning_library.models import Block, BlockResource

logger = logging.getLogger(__name__)

TEST_USER_NAME = "test-student"
TEST_USER_PW = "test-student-pw-123"
TEST_USER_EMAIL = "test-student@example.com"


class TestBasicCourseFeatures(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        """
        Create a basic course and user, so we can test some basic course features,
        like downloading a transcript.
        """
        super(TestBasicCourseFeatures, cls).setUpClass()
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
        super(TestBasicCourseFeatures, cls).tearDownClass()

    def setUp(self):
        """
        Set up data common to all tests.
        """
        super().setUp()

        course = CourseFactory()
        self.course_base_url = course.course_url
        self.course = course

        logger.debug(course.milestones)

        user = UserFactory(username=TEST_USER_NAME,
                           password=TEST_USER_PW,
                           email=TEST_USER_EMAIL)
        user.save()
        EmailAddress.objects.update_or_create(user=user,
                                              email=TEST_USER_EMAIL,
                                              defaults=dict(
                                                primary=True,
                                                verified=True))
        self.user = user

        # Make sure student is enrolled
        enrollment = EnrollmentFactory(course=course,
                                       student=user,
                                       active=True)
        self.enrollment = enrollment

    def _sign_in(self):
        """
        Sign in the current user.
        """
        self.selenium.get(f"{self.live_server_url}/accounts/login?next=/catalog/TEST/SP/")
        username_input = self.selenium.find_element(By.ID, 'id_login')
        username_input.send_keys(TEST_USER_NAME)
        password_input = self.selenium.find_element(By.ID, 'id_password')
        password_input.send_keys(TEST_USER_PW)
        login_button = self.selenium.find_element(By.ID, 'sign_in_btn')
        login_button.click()
        self.selenium.implicitly_wait(5)

    def test_video_and_video_transcript_download_appear(self):

        if not self.selenium:
            return

        # Make student is signed in before continuing...
        self._sign_in()

        # Go to video page and try to download resource
        self.selenium.get(f"{self.live_server_url}/courses/TEST/SP/content/"
                          f"basic_module/basic_section_1/course_unit_1/")
        self.selenium.implicitly_wait(5)

        video_block = Block.objects.filter(slug='video_for_unit_1').first()

        # Video div
        video_div = self.selenium.find_element(By.ID, f"block_{video_block.id}")
        self.assertIsNotNone(video_div)

        # Download transcript button
        block_resource = BlockResource.objects.get(block=video_block)
        download_transcript_btn = self.selenium.find_element(By.ID, f"block_resource_{block_resource.id}")
        self.assertIsNotNone(download_transcript_btn)

    def test_course_progress(self):

        if not self.selenium:
            return

        # Add more milestones to the course, so we can test all types
        MilestoneFactory.create(
            course=self.course,
            name="Test Videos Watched",
            slug="videos_watched",
            description="Watch one video",
            type=MilestoneType.VIDEO_PLAYS.name,
            count_requirement=1,
            required_to_pass=True
        )

        MilestoneFactory.create(
            course=self.course,
            name="Test SITs used",
            slug="sits_used",
            description="Interact with one SIT",
            type=MilestoneType.SIMPLE_INTERACTIVE_TOOL_INTERACTIONS.name,
            count_requirement=1,
            required_to_pass=True
        )

        # Make student is signed in before continuing...
        self._sign_in()

        # Visit the Progress page -- should show no progress yet
        self.selenium.get(f"{self.live_server_url}/courses/TEST/SP/progress/overview")
        milestones_table = self.selenium.find_element(By.XPATH, "//table")
        self.assertIn("Test Course Passed Milestone Answer one assessments to pass course 1 --", milestones_table.text)
        self.assertIn("Test Videos Watched Watch one video 1 --", milestones_table.text)
        self.assertIn("Test SITs used Interact with one SIT 1 --", milestones_table.text)

        # Go to video page and try to play the video
        self.selenium.get(f"{self.live_server_url}/courses/TEST/SP/content/"
                          f"basic_module/basic_section_1/course_unit_1/")
        self.selenium.implicitly_wait(5)

        video_block = Block.objects.get(slug='video_for_unit_1')
        video_div = self.selenium.find_element(By.ID, f"block_{video_block.id}")
        self.assertIsNotNone(video_div)

        self.selenium.switch_to.frame(
            self.selenium.find_element(By.XPATH, '//iframe[starts-with(@src, "https://www.youtube.com/embed")]'))

        self.selenium.implicitly_wait(2)

        play_button = self.selenium.find_element(By.XPATH, "//button[@aria-label='Play']")
        self.selenium.execute_script("arguments[0].scrollIntoView();", play_button)
        play_button.click()
        sleep(2)

        # Visit the Progress page -- should show video progress
        self.selenium.get(f"{self.live_server_url}/courses/TEST/SP/progress/overview")
        milestones_table = self.selenium.find_element(By.XPATH, "//table")
        self.assertIn("Test Course Passed Milestone Answer one assessments to pass course 1 --", milestones_table.text)
        self.assertIn("Test Videos Watched Watch one video 1 1", milestones_table.text)
        self.assertIn("Test SITs used Interact with one SIT 1 --", milestones_table.text)
