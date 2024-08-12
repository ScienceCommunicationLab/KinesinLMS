# ALL AUTH HACK TO PREVENT EMAIL RESET SPAM
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import logging

logger = logging.getLogger(__name__)


def mock_do_not_send_unknown_account_password_reset_email(self, request, email):
    # no operation. This is a monkeypatch to prevent email reset spam.
    logger.warning(f"mock_do_not_send_unknown_account_password_reset_email: Pretending to send "
                   f"password reset email to {email} but not really sending it, since this is not a registered "
                   f"user and probably spam.")
    pass
