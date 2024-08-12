from django.contrib.sites.models import Site


class SiteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set the 'site' context variable
        request.site = Site.objects.get_current()
        response = self.get_response(request)
        return response
