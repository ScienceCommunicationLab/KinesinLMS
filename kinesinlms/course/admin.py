from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin


from kinesinlms.course.models import (
    Bookmark,
    Cohort,
    CohortMembership,
    Course,
    CourseNode,
    CoursePassed,
    CourseResource,
    CourseStaff,
    CourseUnit,
    Enrollment,
    EnrollmentSurvey,
    EnrollmentSurveyAnswer,
    EnrollmentSurveyQuestion,
    Milestone,
    MilestoneProgress,
    Notice,
)
from kinesinlms.forum.models import ForumCategory
from kinesinlms.speakers.models import CourseSpeaker
from kinesinlms.survey.models import Survey


class CohortMembershipInline(admin.TabularInline):
    model = CohortMembership
    extra = 0


class CourseSpeakerInline(admin.TabularInline):
    model = CourseSpeaker
    extra = 0


class CohortInline(admin.TabularInline):
    model = Cohort
    extra = 0


class ForumCategoryInline(admin.TabularInline):
    model = ForumCategory
    extra = 0


class CourseUnitBlockInline(admin.TabularInline):
    model = CourseUnit
    extra = 0
    fk_name = "unit"


class BlocksInline(admin.TabularInline):
    model = CourseUnit.contents.through
    extra = 0
    show_change_link = True


class NoticesInline(admin.TabularInline):
    model = Notice
    extra = 0
    show_change_link = True


# class SpeakerInline(admin.TabularInline):
#    model = Course.speakers.through
#    extra = 0
#    show_change_link = True


class SurveyInline(admin.TabularInline):
    model = Survey
    extra = 0
    show_change_link = True


@admin.register(CohortMembership)
class CohortMembershipAdmin(admin.ModelAdmin):
    model = CohortMembership
    list_display = ("id", "cohort", "student")
    search_fields = ("student__email", "student__username", "cohort__name")


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    model = Cohort
    list_display = ("id", "course", "name", "slug", "type", "cohort_forum_group")
    # Don't include memberships inline...bogs down admin page
    # inlines = (CohortMembershipInline,)


@admin.register(CourseUnit)
class CourseUnitAdmin(admin.ModelAdmin):
    model = CourseUnit
    search_fields = ("slug", "display_name", "uuid")
    list_display = ("id", "display_name", "slug", "uuid", "course")
    inlines = (BlocksInline,)


@admin.register(CourseStaff)
class CourseStaffAdmin(admin.ModelAdmin):
    model = CourseStaff
    search_fields = ("user", "course")
    list_display = ("id", "user", "course", "role")


@admin.register(CourseNode)
class CourseNodeAdmin(DraggableMPTTAdmin):
    model = CourseNode
    list_display = (
        "tree_actions",
        "indented_title",
        "display_sequence",
        "content_index",
        "display_name",
        "slug",
        "type",
        "release_datetime",
        "purpose",
        "course",
    )
    list_display_links = ("indented_title",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    model = Course
    list_display = (
        "id",
        "display_name",
        "slug",
        "run",
        "enable_certificates",
        "enable_badges",
        "start_date",
        "end_date",
        "advertised_start_date",
        "enrollment_start_date",
        "enrollment_end_date",
        "days_early_for_beta",
        "playlist_url",
    )
    inlines = [
        NoticesInline,
        ForumCategoryInline,
        SurveyInline,
        CohortInline,
        CourseSpeakerInline,
    ]


@admin.register(CourseResource)
class CourseResourceAdmin(admin.ModelAdmin):
    model = CourseResource
    list_display = ("id", "name", "description", "uuid", "resource_file")


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    model = Bookmark


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    search_fields = ("student__username", "student__email")
    list_display = (
        "student",
        "student_email",
        "course",
        "active",
        "beta_tester",
        "created_at",
        "updated_at",
    )
    model = Enrollment

    def student_email(self, obj):
        return obj.student.email


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "slug",
        "course",
        "type",
        "count_requirement",
        "required_to_pass",
    )
    model = Milestone


class MilestoneProgressBlocksInline(admin.TabularInline):
    model = MilestoneProgress.blocks.through
    extra = 0
    show_change_link = True


@admin.register(MilestoneProgress)
class MilestoneProgressAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "milestone",
        "student",
        "course",
        "count",
        "achieved",
        "achieved_date",
    )
    search_fields = ("student__username", "course__slug")
    inlines = (MilestoneProgressBlocksInline,)
    model = MilestoneProgress


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    model = Notice


@admin.register(CoursePassed)
class CoursePassedAdmin(admin.ModelAdmin):
    model = CoursePassed
    search_fields = (
        "course__display_name",
        "course__slug",
        "student__username",
        "student__email",
    )
    list_display = ("id", "course", "student", "anon_username")

    def anon_username(self, obj):
        return obj.student.anon_username


@admin.register(EnrollmentSurvey)
class EnrollmentSurveyAdmin(admin.ModelAdmin):
    model = EnrollmentSurvey
    list_display = ("id", "course")


@admin.register(EnrollmentSurveyQuestion)
class EnrollmentSurveyQuestionAdmin(admin.ModelAdmin):
    model = EnrollmentSurveyQuestion
    list_display = ("id", "question_type", "question")


@admin.register(EnrollmentSurveyAnswer)
class EnrollmentSurveyAnswerAdmin(admin.ModelAdmin):
    model = EnrollmentSurveyAnswer
    list_display = ("id", "enrollment", "enrollment_question", "answer")
