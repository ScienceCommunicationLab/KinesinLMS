<div style="max-width:500px">
![KinesinLMS logo](kinesinlms_logo.png)
</div>

# KinesinLMS

KinesinLMS is a small learning management system (LMS). It's written in Python using the Django web application framework,
with a focus on simplicity and the use of standard, conventional libraries and tools wherever possible. It's maybe halfway between a
standard Django website and a fully featured LMS. A primary goal of the project is to keep the code and related setup as simple as possible.

**Simple to extend**: If you're looking to build something innovative and interesting,
perhaps outside the bounds of the usual e-Learning course, you might not want to spend a lot of time
refactoring a complex LMS to fit your vision. KinesinLMS might be helpful in this case. We try to keep things simple and straightforward,
yet still compelling, for example using HTMX where possible for richer interations, rather than always relying on a heavier
JavaScript framework. Having said that, we do provide a couple of interactive assessment components written in React (see the
DiagramTool and the TableTool) that demonstrate how to get these kind of rich interactive activities in a course. Either way,
KinesinLMS might be a good starting point for you to create your next e-Learning experiment.

**Simple to use**: You might also find this project's reduced feature set helpful if you're a single dev and just need to get some
content into an LMS-style format. You should be able to edit, manage, and build this site with little outside help. The course
authoring tool, "Composer," is a bit rudimentary but serviceable and should probably do most of what you need.

Either way, we hope you find this project a useful starting point for your own LMS-like project.

Heads up: if you're looking to run more standard e-Learning courses for massive amounts of students across a number
of large institutions, KinesinLMS is probably not for you. In fact, it's very very likely not for you. You might look at something
like [Moodle](https://moodle.org/), [Open edX](https://openedx.org/), or [Canvas](https://www.instructure.com/canvas/). Those
apps are engineered to scale wide and high and handle your millions of users.

You'll need to be a Django developer to get this system up and running, but you shouldn't need more than one developer, and
it shouldn't take loads of time to configure, deploy and maintain the site. Again, that's a primary goal of this project. If
you have trouble let us know, and we'll try to address any issues you encounter.

If you're not a developer but can get one to behave and get a KinesinLMS site going for you, you'll probably be able to author and publish
courses without much help. (But again things are still raw so keep that developer email handy.) At this point, it's good for even the
course content author to be a bit tech-savvy: at least somewhat familiar with HTML and Bootstrap 5.3 css classes.
That's because the "Composer" feature is especially raw at the moment, although we hope to make it a bit more useful in the near term.

## Background

KinesinLMS originated as a custom e-Learning platform developed
by [McQuillen Interactive](https://www.mcquilleninterative.com)
for [Science Communication Lab (SCL)](https://www.sciencecommunicationlab.org/) as part of SCL's iBiology Courses project.
SCL funded the work with support from the National Institute for General Medical Sciences (grants numbers R25GM116704 and R25GM139147).

[iBiology Courses](https://courses.ibiology.org) is an e-learning site dedicated to helping university students and
post-graduate researchers become better scientists and enhance career and professional development. The iBiology Courses
e-Learning platform was built from scratch after the team struggled to find a simple platform that could be managed by
one person but flexible enough for SCL's unique e-learning research goals. (If you want to get sense of what a KinesinLMS course
looks like, you could take one of the free courses on iBiology Courses. The UI there is an earlier version of KinesinLMS.)

In 2023, SCL was funded by a supplementary grant from the National Institute for General Medical Sciences to make this custom e-Learning platform open source and available to the broader scientific community. KinesinLMS is the result of that effort!

## Features

Here's a quick list of some of the features KinesinLMS does give you:

- Module, section, unit navigation
- Clean UI based on Bootstrap 5.3.
- A mobile-friendly layout (e.g. most things render well on mobile, but some are a bit desktop-biased).
- "Quick nav" for simple course navigation
- Components for videos, html content, assessments, forum discussions, file downloads, etc.
- Basic assessments: long-form text, multiple choice / poll , "Done" button
- "Simple Interactive Tools": DiagramTool, TableTool
- Badges
- Certificates
- Integration with
  - an external forum service (e.g. Discourse)
  - an external email automation service (e.g. ActiveCampaign)
  - an external badge provider (e.g. Badgr)
  - an external survey provider (e.g. Qualtrics)
- "Composer", a simple course authoring tool
- Course analytics in a dedicated, admin-only tab
- Course search
- Course bookmarks
- LTI 1.3 connection to external tools (in development)

## Funding

KinesinLMS was supported by grant numbers R25GM116704 and R25GM139147 from the National Institute for General Medical Sciences.

## License

KinesinLMS is licensed under the [GNU AFFERO GENERAL PUBLIC LICENSE](https://github.com/ScienceCommunicationLab/KinesinLMS?tab=AGPL-3.0-1-ov-file#readme)

## Documentation

For more detailed information, view the docs folder.

The docs are built automatically to this site's GitHub pages site, so you can always read them there: [https://sciencecommunicationlab.github.io/KinesinLMS/](https://sciencecommunicationlab.github.io/KinesinLMS/)

## Quickstart: Development Setup

A quick overview of the steps required to get started in development:

### Initial setup

Have a look at the docs if this abbrievated list is confusing.

1. Clone this repo.
2. Install the project dependencies.
   - System: use your system package manager to install `libpq-dev`/`postgresql-libs`, `python>=3.9`, `python-dev>=3.9`
   - Server-side: using `python>=3.9`, run `pip install -r requirements/local.txt` to install the packages
     from [requirements/local.txt](./requirements/local.txt).
   - Client-side: `npm install` from the root of the project to install the packages
     from [package.json](./package.json).
3. Copy the `.env.example` to `.env`, change the values as you wish.
   - To make sure the project uses your .env file, add this value to your machine's environment:
     `DJANGO_READ_DOT_ENV_FILE=True`
4. Run a local Redis and Postgres database.
   - You can use the `docker.compose.yml` if you want to use Docker: `docker-compose -f docker-compose.yml up`
   - Adjust the `REDIS_URL` and `DATABASE_URL` in `.env` accordingly.
5. Set up integrations locally (optional):
   - Fill in the `TEST_*` environment variables in the `.env` file.
6. Run all database migrations using `python manage.py migrate`
7. Set up the initial project model instances using `python manage.py setup_all`.
8. Create an admin user in the application: `python manage.py createsuperuser`.
9. The first time you log in as the admin user, watch the django runserver logs to locate the email confirmation link.
   Visit that link to activate the account.

Once you've got the site running, you can load the `demo_course_archive.zip` in the [demo course folder](./development_resources/courses/demo_course/demo_course_archive.zip) via Composer and see what a basic course looks like.

### Basic Development commands

- Build the client-side code in watch mode: `npm run dev`.
- Run the server: `python manage.py runserver`.

### Live reloading and Sass CSS compilation

Make sure you have SASS installed:

```
    npm install -g sass
```

Then run the `watch-styles` npm command to the Sass files and compile them to CSS:

```
    npm run watch-styles
```

(You'll need to do a browser refresh to see the changes.)

### Type checks

Running type checks with mypy:

```
   mypy kinesinlms
```

### Testing

- Server-side: install `firefox` to run selenium tests.
- copy `.env.example` to `_envs/_local/django_test.env`, and update it if needed.

  If you're using docker-compose to run redis and postgres, this file should work without modification.

- Test the complete application by running pytest in the root directory `pytest`.
- Test just the client code by running `npm run test`.

### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

```
    coverage run -m pytest
    coverage html
    open htmlcov/index.html
```

## Docs

This project uses mkdocs to generate docs from files stored in the /docs directory.

To build docs locally, make sure you've included all your Django env variables in your current shell.
Then cd into /docs and then run:

```
      mkdocs serve
```

This will run a mkdocs server on your local machine where you can view the docs. Feel free to
suggest changes and additions to the docs as you use KinesinLMS.
