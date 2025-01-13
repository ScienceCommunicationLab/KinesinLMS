import logging
from time import sleep

from allauth.account.models import EmailAddress
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver

from kinesinlms.course.models import Enrollment
from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.learning_library.models import Block
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.models import TrackingEvent
from kinesinlms.users.models import User

logger = logging.getLogger(__name__)

TEST_USER_NAME = "test-student"
TEST_USER_PW = "test-student-pw-123"
TEST_USER_EMAIL = "test-student@example.com"


class TestVideoEvents(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        """
        Make sure the correct events are reaching the database when a
        student views a unit with a video and then interacts with the video.
        """
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

        course = CourseFactory.create(self_paced=True)
        cls.course_base_url = course.course_url
        cls.course = course
        user = User.objects.create_user(username=TEST_USER_NAME, password=TEST_USER_PW, email=TEST_USER_EMAIL)
        user.save()

        email_address, created = EmailAddress.objects.get_or_create(user=user, email=TEST_USER_EMAIL)
        email_address.primary = True
        email_address.verified = True
        email_address.save()

        cls.user = user

        # Make sure student is enrolled
        enrollment = Enrollment.objects.create(course=course, student=user, active=True)
        cls.enrollment = enrollment

    @classmethod
    def tearDownClass(cls):
        if cls.selenium:
            cls.selenium.quit()
        super().tearDownClass()

    def test_video_events(self):
        if not self.selenium:
            return

        # Make student is signed in before continuing...
        self.selenium.get(f"{self.live_server_url}/accounts/login?next=/catalog/TEST/SP/")
        username_input = self.selenium.find_element(By.ID, "id_login")
        username_input.send_keys(TEST_USER_NAME)
        password_input = self.selenium.find_element(By.ID, "id_password")
        password_input.send_keys(TEST_USER_PW)
        login_button = self.selenium.find_element(By.ID, "sign_in_btn")
        login_button.click()
        sleep(5)

        # Go to video page and make sure we have an event for the page view...
        self.selenium.get(
            f"{self.live_server_url}/courses/TEST/SP/content/" f"basic_module/basic_section_1/course_unit_1/"
        )
        sleep(3)

        try:
            latest_event: TrackingEvent = TrackingEvent.objects.latest("id")
        except Exception:
            logger.exception("No tracking events found")
            self.fail("No tracking events found")

        self.assertEqual(latest_event.event_type, TrackingEventType.COURSE_PAGE_VIEW.value)

        # Make sure video is there
        video_block = Block.objects.get(slug="video_for_unit_1")
        video_div = self.selenium.find_element(By.ID, f"block_{video_block.id}")
        self.assertIsNotNone(video_div)

        # Click play and make sure we see an event
        self.selenium.switch_to.frame(
            self.selenium.find_element(By.XPATH, '//iframe[starts-with(@src, "https://www.youtube.com/embed")]')
        )

        sleep(2)

        # youtubePlayer = self.selenium.get_element_by_id("movie_player")
        # youtubePlayer.getPlayerState();

        play_button = self.selenium.find_element(By.XPATH, "//button[@aria-label='Play']")
        self.selenium.execute_script("arguments[0].scrollIntoView();", play_button)
        play_button.click()

        sleep(5)

        video_id = video_block.json_content["video_id"]

        latest_event: TrackingEvent = TrackingEvent.objects.latest("id")
        self.assertEqual(latest_event.event_data["video_event_type"], TrackingEventType.COURSE_VIDEO_PLAY.value)
        self.assertEqual(latest_event.event_data["video_id"], video_id)

        pause_button = self.selenium.find_element(By.XPATH, "//button[@title='Pause (k)']")
        self.selenium.execute_script("arguments[0].scrollIntoView();", pause_button)
        pause_button.click()

        sleep(5)

        latest_event: TrackingEvent = TrackingEvent.objects.latest("id")
        self.assertEqual(latest_event.event_data["video_event_type"], TrackingEventType.COURSE_VIDEO_PAUSE.value)
        self.assertEqual(latest_event.event_data["video_id"], video_id)
