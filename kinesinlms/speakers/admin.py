from django.contrib import admin

from kinesinlms.speakers.models import Speaker, CourseSpeaker


class CourseInline(admin.TabularInline):
    model = Speaker.courses.through
    extra = 0


class BlockInline(admin.TabularInline):
    model = Speaker.blocks.through
    extra = 0


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    model = Speaker
    list_display = ('id', 'full_name', 'title', 'institution', 'video_url', 'slug', 'appears_in')
    inlines = (CourseInline, BlockInline,)

    def appears_in(self, obj):
        return "\n".join([c.token for c in obj.courses.all()])


@admin.register(CourseSpeaker)
class CourseSpeakerAdmin(admin.ModelAdmin):
    model = CourseSpeaker
    list_display = ('id', 'speaker', 'course', 'has_course_headshot')

