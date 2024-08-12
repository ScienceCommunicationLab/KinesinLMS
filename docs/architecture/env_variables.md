# Environment Variables

Most configuration information is stored in the KinesinLMS database. However, some information that is secret
and shouldn't be stored in the DB, is stored in the environment alongside the usual Django settings
(following the still-relevant [12 Factor App](https://12factor.net/config) conventions).

The following environment variables should be configured if the user wants to use various services.
For an example of how to set these variables, see the `env.example` file in the root of the project.

## Email Service

To send email directly, Django must be configured with to use an email gateway. Most gateways use
a token for API call authentication.

    EMAIL_SERVICE_TOKEN="(some API key from email service)"

!!! note
    Along with setting this environment variable, the correct variant of the
    [AnyMail](https://anymail.dev/en/stable/installation/) library must be set in `production.txt`
    requirements file, and AnyMail configured in production.py

## Email Automation Provider

If an email automation provider is being used, most information will be stored in the
EmailAutomationProvider model and updated through the KinesinLMS management panel.

However, the following key should be set and stored in the environment:

    EMAIL_AUTOMATION_PROVIDER_API_KEY="(some API key from email automation service)"

## Survey Provider

If a survey provider is being used, most information will be stored in the SurveyProvider model
and updated through the management panel.

However, the following key should be set and stored in the environment:

    SURVEY_PROVIDER_API_KEY="(some api key from survey provider)"

## Forum Provider

If a forum provider is being used, most information will be stored in the ForumProvider model
and updated through the management panel.

However, the following keys should be set and stored in the environment:

    FORUM_API_KEY="(some API key from forum provider service)"
    FORUM_SSO_SECRET="(some SSO secret from forum provider service)"
    FORUM_WEBHOOK_SECRET="(some webhook secret from forum provider service)"

## Badge Provider

If a badge provider is being used, most information will be stored in the BadgeProvider model
and updated through the management panel.

However, the following should be set and stored in the environment:

    BADGE_PROVIDER_USERNAME="(some username from badge provider service)"
    BADGE_PROVIDER_PASSWORD="(some password from badge provider service)"

## Other Integrations

If you use Sentry (highly recommended), set the DSN for your project in the SENTRY_DSN environment variable.

    SENTRY_DSN="(some DSN from Sentry)"

If you have recaptcha set up with Google, you can configure it with the following:

    RECAPTCHA_USE_RECAPTCHA=False
    RECAPTCHA_PUBLIC_KEY=(some public key)
    RECAPTCHA_PRIVATE_KEY=(some private key)

## Other Env Variables

For more infomation on other standard environment variables to configure Django and Celery, see the .env.example
file in the root of the project.
