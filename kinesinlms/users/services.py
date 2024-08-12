import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.timezone import now

from kinesinlms.course.models import Cohort
from kinesinlms.users.models import InviteUser

User = get_user_model()

logger = logging.getLogger(__name__)

# These users will be used for testing in dev and staging
# so ok to send real emails to them.
TEST_INVITE_USERS = [
    "daniel.mcquillen@gmail.com"
]


class InviteService:

    def invite_user(self, email: str, cohort: Cohort) -> InviteUser:
        """
        Invite a user to register with V2. When the register successfully,
        they should be auto-enrolled in the course for the given cohort.
        """

        if not email:
            raise ValueError("'email' argument cannot be None")
        if not cohort:
            raise ValueError("'cohort' argument cannot be None")

        if User.objects.filter(email=email).exists():
            raise ValueError(f"User with email '{email}' already exists.")

        invite_user, created = InviteUser.objects.get_or_create(email=email, cohort=cohort)
        if created:
            logger.info(f"InviteService: created InviteUser for "
                        f"email {email} cohort {cohort} course {cohort.course}")

        # Compose and send email to user, including invite_user id in registration link
        try:
            self._send_invite_email(invitee_email=email, cohort=cohort)
        except Exception as e:
            logger.exception(f"Could not send invite email to {email}")
            raise Exception("Email could not be sent") from e

        invite_user.email_sent_date = now()
        invite_user.save()

        return invite_user

    def _send_invite_email(self, invitee_email, cohort):
        email_from = "courses@kinesinlms.org"
        email_to = invitee_email
        course_name = cohort.course.display_name

        course_program = None
        if cohort.institution:
            course_program = cohort.institution.name

        email_subject = f"Invite: register with KinesinLMS to take the course '{course_name}'"
        if not email_subject:
            raise Exception("missing email subject")

        base_url = f"https://{Site.objects.get_current().domain}/"
        account_lookup_path = reverse('account_signup')
        registration_url = f"{base_url}{account_lookup_path}"

        params = {
            "course_program": course_program,
            "course_name": course_name,
            "registration_url": registration_url,
            "invitee_email": invitee_email
        }

        msg_plain = render_to_string(f"users/email/invite_to_enroll.txt", params)
        msg_html = render_to_string(f"users/email/invite_to_enroll.html", params)

        # Only send emails to regular email addresses when we're in production.
        # Taking this precaution as staging will at times be set up
        # *exactly* like production, including cron jobs that send survey emails.
        if settings.DJANGO_PIPELINE != "PRODUCTION":
            # only send email if it looks like a test email
            if invitee_email not in TEST_INVITE_USERS and \
                    email_to.split("@")[1] not in ['example.com']:  # add other test domains here.
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
            error_message = f"InviteService: send_mail was not able to send message (returned 0)."
            logger.exception(error_message)
            raise Exception(error_message)

        logger.debug(f"InviteService: Invite email sent! Send_mail result: {result}")
