# Local Setup

This page describes how to set up KinesinLMS on your local machine. It's biased towards macOS, but the steps are
similar for other operating systems. If you prefer Docker-based installs, there is a Dockerfile, but it's not documented
yet, so you might have to rely on the Cookiecutter Django docs for help with that: <https://cookiecutter-django.readthedocs.io/en/latest/developing-locally-docker.html>

## Prerequisites

You should already have the following applications installed on your macOS system. Most can be installed via `brew`.

- Redis
- PostgreSQL
- Node (and npm)
- Python ( preferrably 3.12.1 or later )
- Virtualenvwrapper <https://virtualenvwrapper.readthedocs.io/en/latest/command_ref.html>  

## Virtual Environment

Create a virtualenv for the project. On macOS, with Virtualenvwrapper installed, you can do this with the following command
(assuming your python3 is at `/usr/local/bin/python3`):

```bash
    mkvirtualenv --python=/usr/local/bin/python3 kinesinlms
```

If your environment isn't already activated, activate it:

```bash
workon kinesinlms
```

Next, install the project's python dependencies:

```bash
    pip install -r requirements/local.txt
```

After that, we'll install tools to help us build the project's javascript dependencies.

Although KinesinLMS tries to keep any javascript build steps to a minimum, we still need to build a few javascript
libraries from source definitions like those in `static/src/` and in `kinesinlms_components`. You will need to have npm
and node installed to build these javascript and typescript source files.

If you're on macOS and you don't have those installed, you can install them with homebrew:

```bash
    brew install node
```

Then, install the project's javascript dependencies:

```bash
    npm install
```

And finally, build the client code:

```bash
    npm run build
```

This creates the bundled javascript files needed by the app (mainly for the advanced assessment tools like
DiagramTool and TableTool).

While you're working, you'll want the scss to compile to css automatically. You can do that with the following command:

```bash
    npm run watch-styles
```

There's no command to watch and recompile the javascript files, but that shouldn't be too hard to write if you get tired
calling `npm run build` after changing any javascript files.

## Set up environment variables

You'll need some basic enviroment variables set to run the project. These variables will look slightly different
when you're running locally as compared to when you're running in development, staging or production on your host platform.

When setting up to run locally, you can copy the example file `.env.example` to a file like `_envs/_local/django.env`,
and then change the values as you wish (you'll need to know a bit about how Django uses these variables).
Make sure to configure your IDE to load the values in `_envs/_local/django.env` when running the Django server, shell, or a management command.

By default, KinesinLMS installs `pytest-dotenv` as a dependency in local.txt, so that library will already be available to you. Therefore,
if you're using VS Code, you can just add a line like `"envFile": "${workspaceFolder}/_envs/_local/django.env"` to the correct
configuration to have the .env file values loaded when running Django. More here: <https://pypi.org/project/python-dotenv/#getting-started>

## Database

For this next step, you'll need PostgreSQL set up on your machine and running. If you don't have it installed, you can
install it with homebrew:

```bash
    brew install postgres
```

Then, start the postgres server:

```bash
    brew services start postgres
```

Create a PostgreSQL database for our local development:

```bash
    psql -c "CREATE DATABASE kinesinlms;"
```

Then, migrate the database:

```bash
    python manage.py migrate
```

## Django Setup

You'll probably want a Django superuser to manage the system, so create one now:

```bash
    python manage.py createsuperuser
```

You'll also need to set up some initial model instances and do a few other configuration steps to get
the app ready. We've created a `setup_all` management command to do that. Feel free to extend that command
to do other initial setup tasks you require.

```bash
    python manage.py setup_all
```

## Redis Setup

KinesinLMS uses Redis for managing background tasks. You'll need to have Redis installed and running
if you want to run these background tasks locally. Otherwise, you can set the `CELERY_TASK_ALWAYS_EAGER` setting
to `True` in your local environment to run the tasks synchronously.

If you don't have Redis installed, you can install it with homebrew:

```bash
    brew install redis
```

Then, start the Redis server:

```bash
    brew services start redis
```

You'll now need to run Celery as a separate task. You can do that with the following command in your project's
root directory. Make sure all the environment variables are set before running this...especially
`DJANGO_SETTINGS_MODULE=config.settings.local` ... just like when running Django.

```bash
    celery -A config worker -Q celery -l DEBUG
```

## Third-party Services When Developing Locally

As you know, KinesinLMS relies on third-party services for more complex features like forums or email automations.
That makes it a bit harder to replicate those systems when developing locally, although there are options:

### Discourse Forums

If you're going to use Discourse as a forum service, you'll probably want to run Discourse locally, which isn't exactly easy,
but is relatively straightforward if you're familiar with Docker. You can run a docker image of Discourse and configure
it to look similar to your production environment.

View the ["Local Discourse Setup"](../forum/local_setup.md) page in the "Forum" section for more information.

### Surveys

If you want to have surveys in your course, the only option at the moment is Qualtrics, although we plan to add
other survey providers. There isn't a way to really run Qualtrics locally, so the best option is to create an
account and then create surveys for use in local course development and testing.

View the [Surveys](../surveys/surveys_overview.md) section for more info.

### Badges

You'll need to create a (free) account with Badgr <https://badgr.com/> to support course completion badges.
Here too it's probably best to create an issuer and badge classes just for your local development and testing.

View the [Badges](../badges/badges_overview.md) section for more info.

### Email Automations

The only provider currently supported is ActiveCampaign, although once again we plan to add support for other
email automation services in the future. ActiveCampaign does allow  "developer sandbox accounts" to be set up for free,
so that's an option if you want to include email automations when running locally: <https://developers.activecampaign.com/page/developer-sandbox-accounts>

View the [Email Automation](../email/email_automation_overview.md) section for more info.
