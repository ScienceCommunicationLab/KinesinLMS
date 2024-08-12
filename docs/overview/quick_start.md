# Quick Start

This page provides a brief overview of how to get KinesinLMS set up on your local machine and populated with a "Demo" course.

These instructions assume you have some development experience and understand the basics of things like installing and using PostgreSQL or Redis, or using Python virtual environments. If you don't, this part will be a bit tricky, and you might want to get some help.

This process is described in more detail on the [Local Setup](../development/local_setup.md) page in the Development section.

For actually deploying a site, review the `deployment` section.

1. Clone the KinesinLMS repo to your local machine. `git clone <https://github.com/ScienceCommunicationLab/KinesinLMS/>` and `cd KinesinLMS`  into the newly created directory.
2. Install the project dependencies.
    1. **System**: use your operating system's package manager or installation program to install `postgresql`, `python>=3.9`, `redis`, `node`, and `npm`. Unfortunately there's a bit of complexity here that's outside the scope of these docs. The Django Cookie Cutter documentation has more details on this step: <https://cookiecutter-django.readthedocs.io/en/latest/developing-locally.html>
    2. **Server-side**: using `python>=3.9` in a virtual environment, run `pip install -r requirements/local.txt` to install the packages
     from `requirements/local.txt`. More on creating virtual environments here: <https://docs.python.org/3/library/venv.html>
    3. **Client-side**: run `npm install` from the root of the KinesinLMS project to install the node packages
     from `package.json`. Then run `npm run build` to build the KinesinLMS javascript files.
3. Copy the `.env.example` to `.env`, change the values as you wish.
    - To make sure the project uses your .env file, add this value to your shell's environment variables:
     `DJANGO_READ_DOT_ENV_FILE=True`
4. Run a local Redis and Postgres database.
    - You can use the `docker.compose.yml` if you want to use Docker: `docker-compose -f docker-compose.yml up`
    - Adjust the `REDIS_URL` and `DATABASE_URL` in `.env` accordingly.
5. Set up integrations locally (optional):
    - Fill in the `TEST_*` environment variables in the `.env` file.
6. Run all database migrations using `python manage.py migrate`
7. Set up the initial project model instances KinesinLMS expects using `python manage.py setup_all`.
8. Create an admin user in the application: `python manage.py createsuperuser`.
9. The first time you log in as the admin user, watch the django runserver logs to locate the email confirmation link.
   Visit that link to activate the account. (This is a usual step when using AllAuth for authorization.)
10. Load the `.env` variables into your current shell, and then run the Django server `python manage.py runserver 8000`

Then, log in and navigate to the "Composer" tab. There, you can click Course > Import Course and load the demo_course_archive
stored in `resources/courses/demo_course/demo_course_archive.zip`. You should now see this course in the Course Catalog and be able to enroll in
it and view what a basic course looks like on KinesinLMS.
