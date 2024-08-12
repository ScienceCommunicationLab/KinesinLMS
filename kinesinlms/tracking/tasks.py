import json
import logging
from typing import Dict, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from config import celery_app
from kinesinlms.core.utils import get_aws_lambda_client

logger = logging.getLogger(__name__)

KINESINLMS_EVENTS_LAMBDA = settings.AWS_KINESINLMS_EVENTS_LAMBDA

User = get_user_model()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# SEND TRACKING EVENTS TO SERVICE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 10}, retry_backoff=True)
def send_tracking_event_to_aws(event_dict: Dict) -> Optional[str]:
    """
    Submits a tracking event to an AWS lambda function
    that handles incoming events from kinesinlms.

    This lambda function may perform additional processing
    on the event, at the very least storing it in CloudWatch
    for later analysis.

    Args:
        event_dict:     Dictionary of event data to send to AWS Lambda

    Returns:
        status_code:    Status code from AWS Lambda invocation, otherwise None
    """
    assert event_dict is not None

    if KINESINLMS_EVENTS_LAMBDA:
        # No lambda function configured, so don't send event
        return None

    aws_client = get_aws_lambda_client()

    payload = json.dumps(event_dict, cls=DjangoJSONEncoder)

    try:
        response = aws_client.invoke(
            FunctionName=KINESINLMS_EVENTS_LAMBDA,
            InvocationType='Event',
            LogType='Tail',
            Payload=payload,
        )
    except Exception:
        logger.exception("Error sending tracking event to AWS Lambda.")
        return None

    status_code = response.get('StatusCode', None)
    return status_code


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 10}, retry_backoff=True)
def send_tracking_event_to_slack(event_dict: Dict, message: str):
    course_slug = event_dict.get('course_slug', None)
    if course_slug:
        course_slug = course_slug.lower()
        channel = f"v2-course-{course_slug}"
    else:
        channel = f"v2-admin"
    sc = WebClient(settings.DJANGO_SLACK_TOKEN)
    response = None
    if settings.TEST_RUN:
        message = "(TEST RUN) " + message
    elif settings.DEBUG:
        message = "(DEBUG) " + message
    try:
        response = sc.chat_postMessage(channel=channel, text=message)
    except SlackApiError as slack_error:
        logger.error(f"Error sending message to Slack. {slack_error}")
    finally:
        logger.debug(f"Slack response {response}")
