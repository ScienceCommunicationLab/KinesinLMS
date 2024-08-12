# System Emails

## Configuration

In order for system emails to work, you must have an account with an email gateway
and then configure your account information in the environment.

For example, if you have an account with [PostMark](https://postmarkapp.com/),
you would set up an API key, and then use that key in the environment:

     EMAIL_SERVICE_TOKEN="(your email API token)"

You'll also need to configure the `production.py` file to reflect the email
provider you're using. If it was PostMark, it might look like this:

     # Anymail (Postmark)
     # ------------------------------------------------------------------------------
     
     # https://anymail.readthedocs.io/en/stable/installation/#installing-anymail
     INSTALLED_APPS += ['anymail']  # noqa F405
     EMAIL_BACKEND = "anymail.backends.postmark.EmailBackend"

     # https://anymail.readthedocs.io/en/stable/installation/#anymail-settings-reference
     ANYMAIL = {
       "POSTMARK_SERVER_TOKEN": env("POSTMARK_SERVER_TOKEN", default=None),
       "SEND_DEFAULTS": {"track_opens": True},
     }

Please consult your email provide for more information on how to configure Django to use it for
system emails.

## Survey Emails

If you're doing any kind of research on your e-Learning effort, surveys can be
really important. They were for us when we developed iBiology Courses (the precursor
to KinesinLMS).

KinesinLMS has a simple feature called "survey emails" that you can set up to
automatically send reminder emails about surveys once a student encounters one
in a course.

## Automating Survey Reminder Emails

There's simple management command that will send out any current survey reminder emails.

Ideally this command would be run once a day, but it could be run more or less frequently if desired.

One way to run it daily is to set up a chron command to run the management command.

To run the task manually: ::

     heroku run python manage.py survey_emails --remote production

On heroku, you can use the use Heroku Advanced Scheduler to run the task each day.

Setting this up is outside the scope of these docs. You can find more
information [here](https://devcenter.heroku.com/articles/scheduler).

Once you have an advanced scheduler set up, you can view the automated task's logs: ::

    heroku logs -t -a (your app name) -d advanced-scheduler
