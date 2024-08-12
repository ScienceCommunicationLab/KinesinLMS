import logging
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.sites.models import Site
from django.test import TestCase
from django.utils.timezone import now

from kinesinlms.core.tests.factories import SiteProfileFactory
from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.survey.constants import SurveyType, SurveyEmailStatus
from kinesinlms.survey.models import SurveyEmail, SurveyProviderType
from kinesinlms.survey.service import SurveyEmailService
from kinesinlms.survey.tests.factories import SurveyFactory, SurveyEmailFactory, SurveyProviderFactory
from kinesinlms.users.tests.factories import UserFactory

logger = logging.getLogger(__name__)


class TestSurveyEmailService(TestCase):

    def setUp(self):
        course = CourseFactory(slug="DEMO", run="SP")
        site = Site.objects.get(id=settings.SITE_ID)
        self.site_profile = SiteProfileFactory(site=site)
        self.course = course
        self.enrolled_user = UserFactory(username="enrolled-user",
                                         email="enrolled_user@example.com")

        self.survey_provider = SurveyProviderFactory.create(datacenter_id="iad1",
                                                            type=SurveyProviderType.QUALTRICS.name)

        self.post_course_survey = SurveyFactory(course=self.course,
                                                provider=self.survey_provider,
                                                survey_id='some-test-survey-id',
                                                type=SurveyType.POST_COURSE.name,
                                                send_reminder_email=True,
                                                days_delay=2,
                                                url="example.com/some/survey/url.html")

    def test_email_due_today_is_sent(self):
        SurveyEmailFactory(user=self.enrolled_user,
                           survey=self.post_course_survey,
                           scheduled_date=now())
        with patch('kinesinlms.survey.service.send_mail', return_value=1):
            sent_emails, not_sent_emails = SurveyEmailService.send_emails()
            self.assertEqual(len(sent_emails), 1)
            sent_email: SurveyEmail = sent_emails[0]
            self.assertEqual(sent_email.status, SurveyEmailStatus.SENT.name)

    def test_email_due_yesterday_is_sent(self):
        yesteday = now() + timedelta(days=-1)
        SurveyEmailFactory(user=self.enrolled_user,
                           survey=self.post_course_survey,
                           scheduled_date=yesteday)
        with patch('kinesinlms.survey.service.send_mail', return_value=1):
            sent_emails, not_sent_emails = SurveyEmailService.send_emails()
            self.assertEqual(len(sent_emails), 1)
            sent_email: SurveyEmail = sent_emails[0]
            self.assertEqual(sent_email.status, SurveyEmailStatus.SENT.name)

    def test_email_due_tomorrow_is_not_sent(self):
        tomorrow = now() + timedelta(days=1)
        SurveyEmailFactory(user=self.enrolled_user,
                           survey=self.post_course_survey,
                           scheduled_date=tomorrow)
        with patch('kinesinlms.survey.service.send_mail', return_value=1):
            sent_emails, not_sent_emails = SurveyEmailService.send_emails()
            self.assertEqual(len(sent_emails), 0)
