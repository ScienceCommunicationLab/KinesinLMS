import logging
from time import sleep

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.select import Select

from kinesinlms.course.models import CohortType, CohortMembership
from kinesinlms.course.tests.factories import CourseFactory, CohortFactory

User = get_user_model()
logger = logging.getLogger(__name__)

TEST_USERS = [
    {
        'username': 'test-student-1',
        'pw': 'test-student-pw-1',
        'email': 'test-student-1@example.com'
    },
    {
        'username': 'test-student-2',
        'pw': 'test-student-pw-2',
        'email': 'test-student-2@example.com'
    },
    {
        'username': 'test-student-3',
        'pw': 'test-student-pw-3',
        'email': 'test-student-3@example.com'
    },
]


class TestManualEnrollment(StaticLiveServerTestCase):
    """
    Make sure we can manually enroll students into the
    correct course and cohort within that course.
    """

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

        # Create course to enroll students in.
        course = CourseFactory()
        cls.course_base_url = course.course_url
        cls.course = course

        CohortFactory.create(course=course,
                             name="Default",
                             slug="DEFAULT",
                             type=CohortType.DEFAULT.name)

        # Create a new cohort we'll enroll students into
        cls.cohort_a = CohortFactory.create(course=course,
                                            name="Cohort A",
                                            slug="cohort-a",
                                            type=CohortType.CUSTOM.name)

        # Create another cohort just so we have more options in the select.
        cls.cohort_b = CohortFactory.create(course=course,
                                            name="Cohort B",
                                            slug="cohort-b",
                                            type=CohortType.CUSTOM.name)

        # Create admin user to do manual enrollments
        admin_user = User.objects.create_user(username="daniel",
                                              password="password",
                                              is_staff=True,
                                              is_superuser=True)

        EmailAddress.objects.get_or_create(user=admin_user,
                                           email="daniel@mcquilleninteractive.com",
                                           verified=True,
                                           primary=True)
        cls.admin_user = admin_user

        # Create students to be enrolled

        test_students = []
        for student_data in TEST_USERS:
            user = User.objects.create_user(username=student_data['username'],
                                            password=student_data['pw'],
                                            email=student_data['email'])
            user.save()

            email_address, created = EmailAddress.objects.get_or_create(user=user,
                                                                        email=student_data['email'],
                                                                        verified=True,
                                                                        primary=True)
            email_address.primary = True
            email_address.verified = True
            email_address.save()
            test_students.append(user)
        cls.test_students = test_students

    @classmethod
    def tearDownClass(cls):
        if cls.selenium:
            cls.selenium.quit()
        super(TestManualEnrollment, cls).tearDownClass()

    def test_manual_enrollment_into_default(self):
        """
        Make sure staff can manually enroll three students into DEFAULT cohort.
        """

        if not self.selenium:
            return

        # self.client.force_login(self.admin_user)

        # Make sure admin is signed in before continuing...
        management_url = reverse('management:students_manual_enrollment')
        self.selenium.get(f"{self.live_server_url}/accounts/login?next={management_url}")
        username_input = self.selenium.find_element(By.ID, 'id_login')
        username_input.send_keys("daniel")
        password_input = self.selenium.find_element(By.ID, 'id_password')
        password_input.send_keys("password")
        login_button = self.selenium.find_element(By.ID, 'sign_in_btn')
        login_button.click()
        self.selenium.implicitly_wait(5)

        course_select_input = self.selenium.find_element(By.ID, "id_course")
        course_select = Select(course_select_input)
        course_select.select_by_value(str(self.course.id))

        self.selenium.implicitly_wait(2)

        # HTMx should have updated the "Cohort" select
        cohort_select_input = self.selenium.find_element(By.ID, "id_cohort")
        cohort_select = Select(cohort_select_input)
        cohort_select.select_by_value(str(self.cohort_a.id))

        self.selenium.implicitly_wait(2)
        emails_input = self.selenium.find_element(By.ID, "id_students")
        for student in self.test_students:
            emails_input.send_keys(f"{student.email}\n")

        self.selenium.execute_script("window.scrollBy(0, 300);")
        sleep(2)

        sign_up_button = self.selenium.find_element(By.ID, 'btn-enroll')
        sign_up_button.click()

        sleep(1)

        # Make sure enrollments happened
        for student in self.test_students:
            cohort_membership = CohortMembership.objects.get(student=student)
            self.assertEqual(cohort_membership.cohort, self.cohort_a)
