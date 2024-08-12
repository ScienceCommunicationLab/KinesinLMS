import json
import logging

from django.contrib.auth import get_user_model
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseServerError,
    Http404,
)
from django.views.decorators.csrf import csrf_exempt

from kinesinlms.survey.models import Survey, SurveyCompletion, SurveyProvider
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.tracker import Tracker

logger = logging.getLogger(__name__)

User = get_user_model()


@csrf_exempt
def student_survey_complete_callback(request):
    """
    Handle survey completion webhook callbacks.
    This method expects four specific variables to be
    defined. This method is based on historical use of
    Qualtrics callbacks but this method could be used by other
    providers if the  shape of the data is the same.

    TODO: Come up with mechanism to support different survey providers
    TODO: with different webhook parameters.
    """
    body_unicode = request.body.decode("utf-8")
    body = json.loads(body_unicode)

    survey_id = body.get("survey_id", None)
    uid = body.get("uid", None)
    callback_secret = body.get("secret", None)

    # The "response_id" is the ID Qualtrics gives to the student's survey submission.
    response_id = body.get("response_id", None)

    # Check that all required data was sent with a value...
    for param in [survey_id, uid, callback_secret, response_id]:
        if not param:
            logger.error(
                f"student_survey_complete_callback(): "
                f"Could not handle survey callback for "
                f"survey_id: {survey_id} "
                f"uid: {uid} "
                f"response_id: {response_id}"
            )
            return HttpResponseBadRequest("Missing survey identifier")

    # Lookup survey provider by callback secret
    try:
        provider = SurveyProvider.objects.get(callback_secret=callback_secret)
    except SurveyProvider.DoesNotExist:
        logger.error("Could not find SurveyProvider by provided secret.")
        raise Http404("Survey provider not found.")

    # Lookup survey
    try:
        survey = provider.surveys.get(survey_id=survey_id)
    except Survey.DoesNotExist:
        logger.exception(
            f"Could not find survey for provider {provider} "
            f"with survey ID {survey_id}"
        )
        raise Http404("Survey not found.")

    # Lookup user
    try:
        user = User.objects.get(anon_username=uid)
    except User.DoesNotExist:
        raise Http404("User not found")

    # Handle event...
    try:
        _handle_survey_completion(survey, user, response_id)
    except Exception:
        logger.exception("Could not save survey response ")
        return HttpResponseServerError(
            status=500,
            content="KinesinLMS could not save survey completion info.",
        )

    return HttpResponse(status=200)


def _handle_survey_completion(survey: Survey, user, response_id: str):
    """
    Handle the notification that the student has completed a survey in an
    external survey provider.
    """

    try:
        survey_completion, created = SurveyCompletion.objects.get_or_create(
            user=user, survey=survey
        )
        survey_completion.times_completed += 1
        survey_completion.save()
    except Exception:
        raise Exception(
            f"Could not save survey completion for user: {user} survey: {survey}"
        )

    try:
        event_data = {
            "survey_provider_slug": survey.provider.slug,
            "survey_provider_type": survey.provider.type,
            "survey_id": survey.survey_id,
            "survey_type": survey.type,
            "response_id": response_id,
            "course": survey.course.token,
            "times_completed": survey_completion.times_completed,
        }

        Tracker.track(
            event_type=TrackingEventType.SURVEY_COMPLETED.value,
            user=user,
            event_data=event_data,
            course=survey.course,
        )
    except Exception:
        raise Exception(
            f"Could not save SURVEY_COMPLETED tracking event for user: {user} survey: {survey}"
        )

    return HttpResponse(status=200)
