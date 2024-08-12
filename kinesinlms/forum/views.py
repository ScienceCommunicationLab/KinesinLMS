import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from kinesinlms.forum.models import ForumTopic
from kinesinlms.forum.utils import get_forum_provider, get_forum_service

logger = logging.getLogger(__name__)

User = get_user_model()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# API Classes and functions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~

# API ERRORS

class ServiceUnavailable(APIException):
    status_code = 503
    default_detail = 'Service temporarily unavailable, try again later.'
    default_code = 'service_unavailable'


# API Views

class TopicViewSet(ViewSet):
    """
    View to list all posts in a topic

    * Requires token authentication.
    * Only admin users are able to access this view.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """
        Return a list of all discussion topics available
        """
        # TODO: List all topics available
        return Response([])

    def retrieve(self, request, pk):
        """
        Return a list of all posts in a topic
        Args:
            request:
            pk:

        Returns:
            HTTP Response
        """

        # TODO: Implement once I've made sure all local
        # TODO: ForumTopic models have valid discourse topic ID
        # Make sure user can view topic
        forum_topic = get_object_or_404(ForumTopic, topic_id=pk)
        service = get_forum_service()
        can_view = service.user_can_view_topic(forum_topic, request.user)
        if not can_view:
            logger.error(f"User {request.user} did not have permission "
                         f"to view discourse topic {forum_topic}")
            response = {'message': 'You do not have permission to view this discourse topic.'}
            return Response(response, status=status.HTTP_403_FORBIDDEN)

        # They can view posts in this topic, so return serialized version.
        try:
            posts = service.get_topic_posts(pk)
        except ConnectionError:
            logger.exception("TopicViewSet: Could not connect to Discourse to get a list of posts in a topic.")
            raise ServiceUnavailable()
        except Exception:
            logger.exception("TopicViewSet: Error getting a list of posts in a topic from Discourse.")
            raise ServiceUnavailable()

        return Response(posts)

    def create(self, request):
        response = {'message': 'Create function is not offered in this path.'}
        return Response(response, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, pk=None):
        response = {'message': 'Update function is not offered in this path.'}
        return Response(response, status=status.HTTP_403_FORBIDDEN)

    def partial_update(self, request, pk=None):
        response = {'message': 'Update function is not offered in this path.'}
        return Response(response, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, pk=None):
        response = {'message': 'Delete function is not offered in this path.'}
        return Response(response, status=status.HTTP_403_FORBIDDEN)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# View functions for Discourse callbacks
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@csrf_exempt
def activity_callback(request):
    """
    Handle a callback from Discourse. Currently, we're just listening
    for posting activity.

    Secret will be passed as X-Discourse-Event-Signature in headers.

    :param request:
    :return:
    """

    logger.debug(f"activity_callback invoked request: {request}")

    try:
        service = get_forum_service()
        json_data = service.read_forum_callback(request)
    except Exception:
        logger.exception("activity_callback(): read_forum_callback() raised Exception")
        return JsonResponse({'error': 'Could not process event '}, status=400)

    if not json_data:
        logger.exception("activity_callback() : received callback from Discourse but response body was empty")
        return JsonResponse({'error': 'Could not process event : empty request body'}, status=400)

    try:
        service.save_forum_callback(json_data)
    except Exception as e:
        logger.exception(f"activity_callback(): save_forum_callback() raised Exception {e}")
        return JsonResponse({'error': f'Could not process event : {e}'}, status=400)

    return HttpResponse(status=204)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# View functions for Discourse SSO
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# We're using Django auth as sign on mechanism, so
# the external forum should route unauthenticated users to
# our login page.

@login_required
def discourse_sso(request):
    service = get_forum_service()
    if not service.provider.enable_sso:
        raise Exception(_("SSO is not enabled for this site's forum provider."))

    payload = request.GET.get('sso')
    signature = request.GET.get('sig')
    try:
        nonce = service.sso_validate(payload, signature, settings.FORUM_SSO_SECRET)
        user = request.user
        url = service.sso_redirect_url(nonce, settings.FORUM_SSO_SECRET, user)
        forum = get_forum_provider()
        if forum:
            if not forum.forum_url:
                raise Exception("No forum_url is defined for the Forum Provider.")
            redirect_url = f"{forum.forum_url}{url}"
            return redirect(redirect_url)
        else:
            raise Exception("No forum is defined for the current site.")
    except Exception:
        logger.exception(f"User {request.user} could not log in via forum SSO.")
        raise Http404(_("Cannot log in to the forum. Contact support for help."))
