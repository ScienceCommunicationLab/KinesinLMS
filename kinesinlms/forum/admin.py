from django.contrib import admin

# Register your models here.
from kinesinlms.forum.models import ForumCategory, ForumSubcategory, ForumTopic, CohortForumGroup, \
    CourseForumGroup


class ForumSubcategoryInline(admin.TabularInline):
    model = ForumSubcategory
    extra = 0


class ForumTopicInline(admin.TabularInline):
    model = ForumTopic
    fields = ('id', 'topic_id', 'topic_slug', 'forum_subcategory')
    extra = 0


@admin.register(ForumCategory)
class ForumCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'category_id', 'category_slug')
    inlines = (ForumSubcategoryInline,)
    model = ForumCategory


@admin.register(ForumSubcategory)
class ForumSubcategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'forum_category', 'course_forum_group', 'cohort_forum_group',
                    'subcategory_id', 'subcategory_slug')
    inlines = (ForumTopicInline,)
    model = ForumCategory


@admin.register(ForumTopic)
class ForumTopicAdmin(admin.ModelAdmin):
    list_display = ('id', 'block', 'forum_subcategory', 'topic_id', 'topic_slug')
    model = ForumTopic


@admin.register(CourseForumGroup)
class CourseForumGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'group_id', 'name')
    model = CourseForumGroup


@admin.register(CohortForumGroup)
class FormCohortGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'group_id', 'name', 'course', 'is_default')
    model = CohortForumGroup
