from enum import Enum
from django.urls import reverse
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http.response import Http404
from django.shortcuts import render, get_object_or_404

from rest_framework import viewsets, permissions
from rest_framework.authentication import SessionAuthentication

from waffle.mixins import WaffleSwitchMixin
from waffle.decorators import waffle_switch

from kinesinlms.core.constants import SiteFeatures
from kinesinlms.course.models import CourseUnit
from kinesinlms.course.serializers import CourseUnitSerializer
from kinesinlms.learning_library.models import (
    Block,
    BlockType,
    LibraryItem,
    LibraryItemType,
)
from kinesinlms.learning_library.serializers import BlockSerializer


class LibaryTabs(Enum):
    UNITS = "units"
    BLOCKS = "blocks"


class CourseUnitListView(LoginRequiredMixin, WaffleSwitchMixin, ListView):
    model = LibraryItem
    template_name = "learning_library/course_unit_list.html"
    context_object_name = "library_items"
    waffle_switch = SiteFeatures.LEARNING_LIBRARY.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ll_url = reverse("learning_library:index")
        context["breadcrumbs"] = [
            {
                "url": ll_url,
                "label": "Learning Library"
            }
        ]
        context["title"] = "Course Units"
        return context

    def get_queryset(self):
        return LibraryItem.objects.filter(type=LibraryItemType.UNIT.name, hidden=False)


class BlockListView(LoginRequiredMixin, WaffleSwitchMixin, ListView):
    model = LibraryItem
    template_name = "learning_library/block_list.html"
    context_object_name = "library_items"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ll_url = reverse("learning_library:index")
        context["breadcrumbs"] = [
            {
                "url": ll_url,
                "label": "Learning Library"
            }
        ]
        context["title"] = "Blocks"
        return context

    def get_queryset(self):
        return LibraryItem.objects.filter(type=LibraryItemType.BLOCK.name,  hidden=False)


@login_required
def index(request):
    # Return list of learning library objects
    library_items = LibraryItem.objects.all().prefetch_related()
    active_tab = LibaryTabs.UNITS.name
    context = {
        "section": "learning_library",
        "title": "Learning Library",
        "description": "A list of all learning objects in KinesinLMS.",
        "library_items": library_items,
        "active_tab": active_tab
    }
    return render(request, "learning_library/index.html", context)


@login_required
@waffle_switch(SiteFeatures.LEARNING_LIBRARY.name)
def item_detail(request, id: str):

    library_item = get_object_or_404(LibraryItem, id=id)

    if library_item.type == LibraryItemType.UNIT.name:
        section_url = reverse("learning_library:course_units")
        section_label = "Course Units"
    elif library_item.type == LibraryItemType.BLOCK.name:
        section_url = reverse("learning_library:blocks")
        section_label = "Blocks"
    else:
        raise Http404("Unsupported library item")

    ll_url = reverse("learning_library:index")
    breadcrumbs = [
            {
                "url": ll_url,
                "label": "Learning Library"
            },
            {  
                "url": section_url,
                "label": section_label
            }
        ]

    context = {
        "section": "learning_library",
        "breadcrumbs": breadcrumbs,
        "title": "Item Details",
    }

    if library_item.type == LibraryItemType.UNIT.name:
        course_unit = library_item.course_unit
        context["description"] = f"Detail of course unit {course_unit.display_name}"
        context["course_unit"] = course_unit
        template = "learning_library/detail/course_unit_detail.html"
    elif library_item.type == LibraryItemType.BLOCK.name:
        block = library_item.block
        context["description"] = f"Detail of block {block.display_name}"
        context["library_block"] = block
        context["library_block"] = block
        if block.type == BlockType.VIDEO.name:
            template = "learning_library/detail/VIDEO_block_detail.html"
        else:
            template = "learning_library/detail/default_block_detail.html"
    else:
        raise Http404("Unsupported library item")

    return render(request, template, context)


@login_required
@waffle_switch(SiteFeatures.LEARNING_LIBRARY.name)
def block_detail(request, uuid: str):
    block = get_object_or_404(Block, uuid=uuid)

    if block.type == BlockType.VIDEO.name:
        template = "learning_library/detail-video.html"
    else:
        template = "learning_library/detail-generic.html"

    context = {
        "section": "learning_library",
        "title": f"Learning Library Item Details",
        "description": f"Detail of block {block.display_name}",
        "ll_block": block,
    }
    return render(request, template, context)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# DRF ViewSets
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ViewSets for new Learning Library feature


class BlockViewSet(viewsets.ModelViewSet):
    serializer_class = BlockSerializer
    authentication_classes = (SessionAuthentication,)
    permission_classes = [permissions.IsAdminUser]
    queryset = Block.objects.all()


class CourseUnitViewSet(viewsets.ModelViewSet):
    serializer_class = CourseUnitSerializer
    authentication_classes = (SessionAuthentication,)
    permission_classes = [permissions.IsAdminUser]
    # TODO: only get CourseUnits that are in LibraryItem
    queryset = CourseUnit.objects.all()
