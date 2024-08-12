# Architecture Overview

KinesinLMS is an [MVC-like](https://docs.djangoproject.com/en/5.0/faq/general/#django-appears-to-be-a-mvc-framework-but-you-call-the-controller-the-view-and-the-view-the-template-how-come-you-don-t-use-the-standard-names) application
that follows the best practices established by the Django project and further refined by
the [CookieCutter Django](https://cookiecutter-django.readthedocs.io/en/latest/) project.

It tries hard to keep the number of components in the system to a minimum to limit how much you, the developer, need to understand and manage:

- **PostgreSQL** for persistence, including JSON object storage and text search vectors.
- **Redis** for in-memory cache, including Celery support.
- **Bootstrap** for UI components. (Yes, excellence can be boring.)
- **HTMx** for 'hypermedia' AJAX interactions.
- **React** only where really needed. (Look at all those npm dependencies go. So many! It's like confetti! Whee!)

Given how complex web application development has become, some industry experts have encouraged thinking critically about
technological complexity and how to reduce it. As Ruby on Rails creator David Heinemeier Hansson [extolled in a recent interview](https://youtu.be/rEZNbM4MUdo?t=3919),
"Simpler. Simpler. We've gone through 40 years in the desert…for necessary but temporary complexity…we built bridges to get
from A to B, and now we're at B and people haven't realized the bridges aren't necessary…individual programmers can
understand the entire system they're working on."

KinesinLMS tries to be one of those simpler applications. Just enough LMS. If it's not, if it misses the mark, can you help make it so?

## "Rich" User Experience

For more immediate and "rich" user experiences, two approaches are taken:

- Simple interactions are handled by HTMx and its 'hypermedia' approach. KinesinLMS prefers this to more involved frameworks like React, Angular or Svelte.
- However, in places where the user interface complexity is high, such as a custom drag-and-drop node diagram tool, React is used.

## PostgresSQL for Persistence

PostgreSQL is powerful. So rather than having a separate DB for an object store (e.g. Mongo) or a specialized tool for
text searches (e.g. Elasticsearch), KinesinLMS uses PostgreSQL for everything.

## Complex Features

Complex features that would be hard to develop and manage internally are offloaded to external resources, which the developer is meant to set up and
integrate via the KinesinLMS dashboard:

- forums are hosted on Discourse
- badges are hosted in Badgr.com
- surveys are hosted in Qualtrics
- email automations are hosted in ActiveCampaign.

## Celery and Asynchronous Queues

Asynchronous queues are a great way to offload long processes so a web request can be returned quickly. (Want to learn more? [Read this](https://realpython.com/asynchronous-tasks-with-django-and-celery/).)

At the moment there aren't many processes in KinesinLMS that need to be offloaded to an asynchronous queue. In fact, at the time of writing
there's just one in the course analytics section.

However, you might find you'll need to use an async queue for a feature you're creating that takes a bit of time, especially as some
platforms can limit web request time (Heroku limits requests to 30 seconds). In these cases, KinesinLMS recommends creating a Celery
task to manage the long-running process.
