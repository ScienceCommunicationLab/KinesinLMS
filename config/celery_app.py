import os
from celery import Celery

# set the default Django settings module for the 'celery' program.
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("kinesinlms")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

if settings.DJANGO_PIPELINE != "LOCAL":
    # We're running on Heroku, so set the redis_backend_use_ssl config var
    # From https://github.com/celery/celery/issues/5371#issuecomment-839075587
    # Event though we did similar updates in production.py, that's for the Cache,
    # whereas this is for celery...
    app.conf.redis_backend_use_ssl = {"ssl_cert_reqs": "none"}

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
