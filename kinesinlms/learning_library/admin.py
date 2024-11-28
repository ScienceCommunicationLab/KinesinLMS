from django.contrib import admin

from kinesinlms.assessments.models import Assessment
from kinesinlms.forum.admin import ForumTopicInline
from kinesinlms.learning_library.models import (
    Block,
    BlockLearningObjective,
    BlockResource,
    LearningObjective,
    LibraryItem,
    Resource,
    UnitBlock,
)
from kinesinlms.sits.models import SimpleInteractiveTool

# Register your models here.


class AssessmentInline(admin.StackedInline):
    model = Assessment
    extra = 0


class BlockLearningObjectiveInline(admin.TabularInline):
    model = BlockLearningObjective
    extra = 0


class BlockResourceInline(admin.TabularInline):
    model = BlockResource
    extra = 0
    show_change_link = True


class BlockSimpleInteractiveToolInline(admin.TabularInline):
    model = SimpleInteractiveTool
    extra = 0
    show_change_link = True


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    model = Block
    list_display = ("id", "type", "display_name", "slug", "status", "tag_list")
    list_display_links = ("id", "display_name")
    search_fields = ("display_name", "slug", "type")
    list_per_page = 50
    inlines = (
        AssessmentInline,
        BlockResourceInline,
        ForumTopicInline,
        BlockSimpleInteractiveToolInline,
        BlockLearningObjectiveInline,
    )

    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())


@admin.register(BlockResource)
class BlockResourceAdmin(admin.ModelAdmin):
    model = BlockResource
    list_display = ("id", "block", "resource", "file_name")
    list_display_links = ("id", "block")
    search_fields = ("block",)
    list_per_page = 50


@admin.register(LibraryItem)
class LibraryItemAdmin(admin.ModelAdmin):
    model = LibraryItem
    list_display = ("id", "block", "hidden", "allow_pathway", "tag_list", "uuid")

    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())


@admin.register(UnitBlock)
class UnitBlockAdmin(admin.ModelAdmin):
    model = UnitBlock
    list_display = (
        "id",
        "course_unit",
        "block",
        "slug",
        "label",
        "block_order",
        "hide",
    )


@admin.register(LearningObjective)
class LearningObjectiveAdmin(admin.ModelAdmin):
    model = LearningObjective
    list_display = ("id", "slug", "type", "tag_list", "description")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")

    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    model = Resource
    search_fields = (
        "uuid",
        "name",
        "type",
        "description",
        "url",
    )
    list_display = (
        "id",
        "slug",
        "name",
        "uuid",
        "type",
        "file_name",
        "url",
        "description",
    )
