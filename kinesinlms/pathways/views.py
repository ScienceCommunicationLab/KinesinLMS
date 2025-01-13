from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser

from kinesinlms.pathways.models import Pathway
from kinesinlms.pathways.serializers import PathwayListSerializer, PathwaySerializer

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Template-based views
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@staff_member_required
def index(request):
    # Return list of learning library objects
    context = {"pathways": Pathway.objects.all(), "title": "Pathways", "description": "A list of all pathways."}
    return render(request, "pathways/index.html", context)


@staff_member_required
def detail(request, pk):
    pathway = get_object_or_404(Pathway, pk=pk)
    description = "A description of pathway <b>{}</b>".format(pathway.display_name)
    context = {
        "can_edit": pathway.author == request.user,
        "pathway": pathway,
        "title": "Pathway Detail",
        "description": description,
    }
    return render(request, "pathways/detail.html", context)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# DRF ViewSets
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ViewSets for new Learning Library feature


class PathwayViewSet(viewsets.ModelViewSet):
    serializer_class = PathwaySerializer
    queryset = Pathway.objects.all()

    authentication_classes = [
        SessionAuthentication,
    ]
    permission_classes = [
        IsAdminUser,
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return PathwayListSerializer
        else:
            return PathwaySerializer
