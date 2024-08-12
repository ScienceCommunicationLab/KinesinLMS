# Heroku Deployment

## Background

Heroku is one of many Platform-as-a-Service (PaaS) providers you could choose from to host your KinesinLMS app,
so make sure you look around at pricing and developer tools before selecting a service. Costs can run up quickly,
so do your homework.

!!! note
    Heroku isn't free. Not even close. They used to have a free tier, but even that is gone. Nothing gold can stay.
    So make sure you investigate Heroku charges (of which there are many) before attempting to deploy to Heroku.
    This project certainly does not recommend Heroku as an affordable option, but it is (still) relatively easy to get
    started. So please do your research on other providers. We hope to include directions for setting up some others (Fly.io, Render.com, etc.) soon.

These instructions describe the basic steps for hosting your site on Heroku, but the steps should be similar
for other services.

These instructions assume you're using Heroku's native build packs, but if you want to use Docker, KinesinLMS
includes a basic Dockerfile that should help you get started.

## Heroku Pipelines

In a typical deployment, you'll want different servers for testing new features, for doing final tests before pushing something
to production, and an actual "live" production server. You can organize these three servers using a Heroku pipline:

- development -- for testing and debugging new features
- staging -- for team testing and validation of production-ready builds
- production -- the live server

You can set the environment variable `HEROKU_PIPELINE`, so that KinesinLMS is
made aware of which of these servers its running on. You can use this information to
modify code accordingly. (E.g. when not running onthe `PRODUCTION` pipeline, perhaps you only
want to emails if they're going to you or some test accounts you've configured.)

!!! note
    You don't have to set up three servers to get going. You could set up only one to limit cost.
    Using 'development', 'staging' and 'production' is a common pattern to help manage new features,
    product testing and production updates.

## Creating Heroku Apps

In this step we'll set up the Heroku apps for the three parts of our pipeline.
We assume you are already familiar with Heroku, have a Heroku account, and have installed the
Heroku CLI on your machine.

These instructions are based on Heroku set up steps provided by Django Cookiecutter.
You can read those instructions here:
[https://cookiecutter-django.readthedocs.io/en/latest/deployment-on-heroku.html](https://cookiecutter-django.readthedocs.io/en/latest/deployment-on-heroku.html)

Create the Heroku apps for each step in our pipeline. Use the name of your app in place of `(your app name)` in the
following steps. For example, your app name might be `so-awesome-university`, because, what's up, it is.

First step up the 'development' server:

    heroku create --buildpack heroku/python --remote development --app (your app name)-development

After running this, you'll notice that Heroku created a new git remote on your local machine that
points to your new 'development' server on Heroku. If you type `git remote -v` you should see that new remote:

    ❯ git remote -v
    development https://git.heroku.com/(your app name)-development.git (fetch)
    development https://git.heroku.com/(your app name)-development.git (push)

Next, create a staging and a production server:

    heroku create --buildpack heroku/python --remote staging --app (your app name)-staging

    heroku create --buildpack heroku/python --remote production --app (your app name)

Next we'll configure a server in the pipeline, adding the resources we'll need, like a database and a cache.

## Configurating Heroku Apps

Once you've created your Heroku apps (servers), you'll need to configure them with the resources they need to operate --
a PostgreSQL database, a Redis cache, and any other services you might need. We can do this using the Heroku CLI.

The following instructions are for configuring the `development` app, but the same steps would apply for `staging` and `production`.

Note that when you have your Heroku apps defined in your local git repository as git remotes, you can just refer to them with `--remote` when
performing command line operations, for example `--remote development` to target the development server.

## PostgreSQL Setup

KinesinLMS uses PostgreSQL as its database. We'll use the Heroku PostgreSQL add-on.

Create a PostgreSQL database:

    heroku addons:create heroku-postgresql:essential-0 --remote development

Schedule backups (since the 'essential-0' plan doesn't include automatic backups):

    heroku pg:backups schedule --at '02:00 America/Los_Angeles' DATABASE_URL --remote development

...and then 'promote' the database to be our primary database (you might not need this step if Heroku already promoted your database in the previous step).

    heroku pg:promote DATABASE_URL --remote development

## REDIS Setup

Parts of KinesinLMS use Redis for caching and other purposes, such as asynchronous tasks run by Celery. So we'll need a
Redis cache available.

Let's add the Heroku Redis add-on:

    heroku addons:create heroku-redis:mini --remote development

KinesinLMS needs to know that Celery is to use this Redis service, so copy the Redis URL into the appropriate env variable:

    heroku config:set CELERY_BROKER_URL=$(heroku config:get REDIS_TLS_URL) --remote development

## Environment Veriables Setup

Just a reminder that a conventional way to get system information into a web application is to use environment variables (see ["III Config"](https://12factor.net/config) in
"The Twelve-Factor App"[https://12factor.net/]). So in this part we set up all the env variables we'll need to configure our app in Heroku.

Let's set up the various environment variables that a basic Django app like KinesinLMS expects. Run these one at a time, so you can see Heroku's response.

    heroku config:set PYTHONHASHSEED=random  --remote development
    heroku config:set WEB_CONCURRENCY=4  --remote development
    heroku config:set DJANGO_DEBUG=False  --remote development
    heroku config:set DJANGO_SECRET_KEY="$(openssl rand -base64 64)"  --remote development

When we set the "admin" URL we'll use a random string...this adds another layer of security rather than just using 'admin'. Of course,
you don't have to use a random string...you could just pick a slightly obfuscated name (e.g. 'so-special-admin').

    heroku config:set DJANGO_ADMIN_URL="$(openssl rand -base64 4096 | tr -dc 'A-HJ-NP-Za-km-z2-9' | head -c 32)/" --remote development

Next let's set the Django settings module. Even though we're running in "development", we want the server to behave as if it's in production,
so we're setting this variable to `config.settings.production`...

    heroku config:set DJANGO_SETTINGS_MODULE=config.settings.production  --remote development

Finally, we should set the allowed hosts. This setting configures Django to only allow certain URLs
to be the app host. If you get a domain name for your server in Heroku, you'll use that here. Until you do,
Heroku will have given your app a generic URL. You can find it in the Heroku panel for your app, under "Settings".
It will look something like this: `https://(your app name)-development-e6ad78551565.herokuapp.com/`.

Use that domain for the DJANGO_ALLOWED_HOSTS variable:

    heroku config:set DJANGO_ALLOWED_HOSTS=(your app name)-development-e6ad78551565.herokuapp.com  --remote development

## AWS Access Setup

By default, KinesinLMS expects to place static and media files in an AWS S3 bucket. However, you can configure it to store these
files somwhere else, like Google Cloud Storage, Digital Ocean Spaces, and so on. Heroku even has some easy plugins you can
use. [More on that here](https://dev.to/heroku/properly-managing-django-media-static-files-on-heroku-o2l).

Since we're defaulting to AWS S3, you'll need to create a bucket on AWS S3 to hold these assets, as well as an AWS IAM user with
access to that bucket. Describing how to create these in AWS is outside the scope of this document, but you can read more about it here:
<https://testdriven.io/blog/storing-django-static-and-media-files-on-amazon-s3/>

!!! note
    If you use AWS S3, be really careful with your configuration. This is one of those places you can't avoid complexity and reading the docs.

Once you've created an S3 bucket for the KinesinLMS app and an IAM user with access to that bucket,
create an access key and secret for that IAM user.

Note that you'll have to do this setup process for each app in your pipeline, so you might name your S3 bucket's accordingly, probably using the
same name as your app and pipelie (e.g. `so-awesome-university-development-s3` for development, `so-awesome-university-staging-s3` for staging, and so on).

The use the AWS settings you've just created to set the following environment values in the Heroku environment ::

    heroku config:set DJANGO_AWS_STORAGE_BUCKET_NAME=(your storage bucket name) --remote development
    heroku config:set DJANGO_AWS_ACCESS_KEY_ID=(your aws access key) --remote development
    heroku config:set DJANGO_AWS_SECRET_ACCESS_KEY=(some django aws secret access key) --remote development
    heroku config:set DJANGO_AWS_S3_REGION_NAME=us-west-1 --remote development

## Custom Environment Variables Setup

There are a few custom environment variables that KinesinLMS uses to configure the application.
We'll set those now:

    heroku config:set DJANGO_PIPELINE="DEVELOPMENT" --remote development

## Pre-Deploy Steps

You're now ready to push the app to heroku. But before you do, make sure you've compiled your
stylesheets, packaged your javascript, and basically got everything ready to go.

### Compile Stylesheets

If there has been any changes to scss files, make sure they're compiled to css files.

In an effort to keep things simple, there's a npm package.json command to watch scss files
directly using sass. (You'll need sass installed on your machine.)

To run sass in watch mode the 'watch-styles' npm command: ::

    npm run watch-styles

When this command is run, all .sass files in the kinesinlms/static/sass directory will be watched
and compiled to .css files in the kinesinlms/static/css directory any time you change something in a .scss file.

## Package Javascript

Make sure all javascript-based components have been transpiled and packaged.
(You'll need node and npm installed on your machine.)
Note that this part of the build step is somewhat rudimentary and will be
improved in the future.

If you're pushing to the PRODUCTION server on the pipeline, that means building minified javascript files:

    npm run build

But if you want to debug on DEVELOPMENT or STAGING, create javascript with source maps:

    npm run dev

This will create compiled javascript files in kinesinlms/static/js.

IMPORTANT: Make sure you add any new or updated files to GitHub before continuing.

## Deploy to Heroku

IMPORTANT: Make sure you add any new or updated files from the previous steps to your git repository before continuing,
otherwise they won't get pushed to Heroku in the next step.

DOUBLY-IMPORTANT: Make sure all your tests are passing before pushing to production.

Pushing your project to Heroku is as simple as pushing to GitHub.

    git push development master

(If you were pushing to `staging` or `production` you'd just replace `development` with that target.)

When you push your code, Heroku will automatically rebuild your app, including running any required migrations.

## Post-deploy

If you're setting up a server for the first time (or just cleaned out DEVELOPMENT and
want to set up initial data), run the following management to create a superuser for yourself:

    heroku run python manage.py createsuperuser --remote development

Also, you may want to configure KinesinLMS with some initial data. There's a management command
called `setup_all` that you can customize to set up your server with some initial users, or speakers,
or whatever. The default implementation of this command simply sets up a Site instance.

To run this command if you're setting up DEVELOPMENT:

    heroku run python manage.py setup_all --remote development

## Open your app

At this point, if you navigate to your apps URL (or just type 'heroku open' in the project directory), you should see your site!
