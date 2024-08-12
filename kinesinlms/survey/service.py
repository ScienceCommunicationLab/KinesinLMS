import logging
from datetime import timedelta, date
from typing import List, Tuple

from django.conf import settings
from django.core.mail import send_mail
from django.template import loader
from django.template.loader import render_to_string
from django.utils.timezone import now

from kinesinlms.core.models import SiteProfile
from kinesinlms.core.utils import get_current_site_profile
from kinesinlms.survey.constants import SurveyEmailStatus, SurveyType
from kinesinlms.survey.models import SurveyEmail, Survey

logger = logging.getLogger(__name__)


class SurveyEmailService:
    """
    Simple class to encapsulate methods that handle sending survey emails.
    We don't use email automations services for this as we want to be able to
    keep tight control over email contents and timing.
    """

    @classmethod
    def send_emails(cls) -> Tuple[List[SurveyEmail], List[SurveyEmail]]:
        """
        Read in all SurveyEmail objects that have a scheduled_date for today or earlier.
        Send each email and mark as processed, or as error if there's trouble reading or sending.

        Returns:
            List of SurveyEmails sent
            List of SurveyEmails not sent

        """
        today_date = now()
        logger.info(f"Running 'survey_emails' management command for {today_date.isoformat()}.")

        survey_emails = cls.get_survey_emails_to_send(less_than_date=today_date)

        count = 0
        errors = 0
        sent = []
        not_sent = []

        if not survey_emails:
            logger.info("SurveyEmailService: No emails to send today!")
            return sent, not_sent

        logger.info(f"SurveyEmailService: Found {len(survey_emails)} survey emails to send.")
        for survey_email in survey_emails:
            try:
                cls.send_survey_email(survey_email)
                survey_email.status = SurveyEmailStatus.SENT.name
                survey_email.save()
                logger.info(f"SurveyEmailService: Send survey email to {survey_email.user.email}")
                sent.append(survey_email)
            except Exception:
                logger.exception(f"SurveyEmailService: Couldn't send survey email id {survey_email.id}")
                survey_email.status = SurveyEmailStatus.ERROR.name
                survey_email.save()
                not_sent.append(survey_email)

        logger.info(f"SurveyEmailService: Finished sending emails. count={count} errors={errors}.")
        return sent, not_sent

    @classmethod
    def get_survey_emails_to_send(cls, less_than_date) -> List[SurveyEmail]:
        results = SurveyEmail.objects.filter(scheduled_date__lte=less_than_date,
                                             status=SurveyEmailStatus.UNPROCESSED.name).all()
        return results

    @classmethod
    def send_survey_email(cls, survey_email: SurveyEmail):
        """
        Attempts to send a survey email to a user.

        Args:
            survey_email:   SurveyEmail object to send.

        Returns:
            ( Nothing )

        Raises:
            Exception if there's a problem sending the email.
        """

        site_profile: SiteProfile = get_current_site_profile()

        email_from = site_profile.support_email
        if not email_from:
            email_from = settings.CONTACT_EMAIL
            if not email_from:
                raise Exception("Cannot send survey email since no support email "
                                "is defined in SiteSettings nor a CONTACT_EMAIL in settings.py")

        email_to = survey_email.user.email
        if not email_to:
            raise Exception("missing email to address")

        email_subject = cls.get_subject(survey_email)
        if not email_subject:
            raise Exception("missing email subject")

        anon_username = survey_email.user.anon_username
        if not anon_username:
            raise Exception("missing anon_username")

        survey_url = survey_email.survey.url
        if not survey_url:
            raise Exception("missing survey_url")

        survey_w_anon_url = f"{survey_url}?uid={anon_username}"

        informal_name = ""
        if survey_email.user.informal_name is not None:
            # Note: make sure there's a space before name
            informal_name = f" {survey_email.user.informal_name}"

        params = {
            "informal_name": informal_name,
            "survey_url": survey_w_anon_url,
            "course_name": survey_email.survey.course.display_name
        }

        survey_type = survey_email.survey.type  # e.g. POST_COURSE
        course_token = survey_email.survey.course.token

        # Look for custom templates for course, otherwise use default
        txt_template = f"survey/email_templates/custom/{course_token}_{survey_type}.txt"
        try:
            loader.get_template(txt_template)
        except loader.TemplateDoesNotExist:
            txt_template = f"survey/email_templates/DEFAULT_{survey_type}.txt"
            try:
                loader.get_template(txt_template)
            except loader.TemplateDoesNotExist:
                raise Exception(f"Missing DEFAULT .txt email template : {txt_template} ")

        html_template = f"survey/email_templates/custom/{course_token}_{survey_type}.html"
        try:
            loader.get_template(html_template)
        except loader.TemplateDoesNotExist:
            html_template = f"survey/email_templates/DEFAULT_{survey_type}.html"
            try:
                loader.get_template(html_template)
            except loader.TemplateDoesNotExist:
                raise Exception(f"Missing DEFAULT .html email template : {html_template} ")

        msg_plain = render_to_string(txt_template, params)
        msg_html = render_to_string(html_template, params)

        # Only send emails to regular email addresses when we're in production.
        # Taking this precaution as staging could be at times be set up
        # *exactly* like production, including cron jobs that send survey emails.
        if settings.DJANGO_PIPELINE != "PRODUCTION":
            # only send email if it looks like a test email
            if email_to.split("@")[1] not in ['kinesinlms.org', 'example.com']:
                error_msg = f"Can't send email to {email_to}...we're not in production!"
                logger.exception(error_msg)
                return

        result = send_mail(
            email_subject,
            msg_plain,
            email_from,
            [email_to],
            html_message=msg_html,
        )
        if result == 0:
            error_message = "send_survey_email() send_mail was not able to send message (returned 0)."
            logger.exception(error_message)
            raise Exception(error_message)

        logger.debug(f"send_survey_email() Complete! Send_mail result: {result}")

    @classmethod
    def get_subject(cls, survey_email: SurveyEmail) -> str:
        """
        TODO: Make a separate subject for each course and survey
        Args:
            survey_email:

        Returns:
            A string to be used for email subject line.
        """

        try:
            survey_type = survey_email.survey.type
            if survey_type == SurveyType.POST_COURSE.name:
                prefix = "Post-course survey: "
            elif survey_type == SurveyType.FOLLOW_UP.name:
                prefix = "Follow-up survey: "
            elif survey_type == SurveyType.PRE_COURSE.name:
                prefix = "Pre-course survey: "
            else:
                prefix = None
            subject = f"{prefix}Tell us what you think about {survey_email.survey.course.short_name}"
            return subject
        except Exception:
            logger.exception("Couldn't get course short_name for 'subject' of survey email")
            return "KinesinLMS Survey : Tell us what you think."

    @classmethod
    def schedule_survey_emails_for_start_of_course(cls, user, course_surveys: List[Survey]):
        """
        Schedule any survey email reminders that should be scheduled when a user
        starts a course.

        Args:
            user:
            course_surveys:     A list of surveys that should have reminder emails
                                scheduled for this user.

        Returns:
            ( nothing )
        """

        relevant_survey_types = [SurveyType.PRE_COURSE.name]
        for course_survey in course_surveys:
            if course_survey.type in relevant_survey_types and course_survey.send_reminder_email:
                try:
                    cls.schedule_survey_email(course_survey, user)
                except Exception:
                    logger.exception(f"Could not schedule SurveyEmail "
                                     f"for survey {course_survey} "
                                     f"and user {user}")

    @classmethod
    def schedule_survey_email(cls, course_survey: Survey, user) -> bool:
        """
        Schedule a reminder email for a survey.

        Args:
            course_survey:      Survey to schedule a reminder email for.
            user:               User to schedule a reminder email for.

        Returns:
            Boolean indicating whether the email is scheduled or not.

        """

        if not course_survey.send_reminder_email:
            logger.warning(f"schedule_survey_email(): Survey {course_survey} "
                           f"is not set to send reminder emails.")
            return False

        try:
            survey_email = SurveyEmail.objects.get(survey=course_survey, user=user)
            logger.info(f"SurveyEmail {survey_email} already exists "
                        f"for course survey {course_survey} "
                        f"and user {user}")
            return True
        except SurveyEmail.DoesNotExist:
            pass

        try:
            date_to_send = date.today() + timedelta(days=course_survey.days_delay)
            survey_email = SurveyEmail.objects.create(survey=course_survey,
                                                      user=user)
            survey_email.scheduled_date = date_to_send
            survey_email.save()

            logger.info(f"Updated existing survey_email for course survey {course_survey} "
                        f"for user {user} "
                        f"to be sent {date_to_send}")
        except Exception:
            logger.exception(f"Could not schedule SurveyEmail "
                             f"for survey {course_survey} "
                             f"and user {user}")
            return False

        return True

    @classmethod
    def unschedule_survey_emails(cls, course, user):
        """
        Delete all UNPROCESSED survey emails for a user in a particular course.
        This method should be called when a user unenrolls.

        Args:
            course:
            user:

        Returns:
            ( nothing )
        """
        course_surveys = Survey.objects.filter(course=course)
        if not course_surveys:
            return

        for course_survey in course_surveys:
            try:
                survey_emails = SurveyEmail.objects.filter(survey=course_survey,
                                                           status=SurveyEmailStatus.UNPROCESSED.name,
                                                           user=user)
                survey_emails.delete()
            except SurveyEmail.DoesNotExist:
                # Nothing to do here. SurveyEmail does exist for this user and survey.
                pass
