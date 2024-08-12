from django.apps import AppConfig

from kinesinlms.core.allauth_password_reset_hack import mock_do_not_send_unknown_account_password_reset_email


class CoreConfig(AppConfig):
    name = 'kinesinlms.core'

    def ready(self):
        """
        Actions to take after apps are loaded.
        """
        # monkeypatch the allauth password reset form to prevent email reset spam
        from allauth.account.forms import ResetPasswordForm
        # Use our no op method to prevent email reset spam
        ResetPasswordForm._send_unknown_account_mail = mock_do_not_send_unknown_account_password_reset_email
