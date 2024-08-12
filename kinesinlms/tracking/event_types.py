# Make sure first three parts of name logically map to an ElasticSearch doctype

# ~~~~~~~~~~~~~~~~~~~~~
# EVENT TYPES
# ~~~~~~~~~~~~~~~~~~~~~
from enum import Enum
from gettext import gettext as _


class TrackingEventType(Enum):
    # SITE AND COURSE INTERACTION EVENTS
    USER_REGISTRATION = "kinesinlms.core.user.registration"
    USER_EMAIL_CONFIRMED = "kinesinlms.core.user.email_confirmed"
    USER_EMAIL_AUTOMATION_PROVIDER_USER_ID_CREATED = "kinesinlms.core.user.email_automation_provider_user_id_created"
    USER_LOGIN = "kinesinlms.core.user.login"
    ENROLLMENT_ACTIVATED = "kinesinlms.core.user.enrollment.activated"
    ENROLLMENT_DEACTIVATED = "kinesinlms.core.user.enrollment.deactivated"

    # BASIC COURSE EVENTS
    COURSE_CUSTOM_APP_PAGE_VIEW = "kinesinlms.course.custom_app.page_view"
    COURSE_EXTRA_PAGE_VIEW = "kinesinlms.course.extra_page.page_view"
    COURSE_HOME_VIEW = "kinesinlms.course.home.page_view"
    COURSE_PROGRESS_VIEW = "kinesinlms.course.progress.page_view"
    COURSE_CERTIFICATE_VIEW = "kinesinlms.course.certificate.page_view"
    COURSE_SPEAKERS_VIEW = "kinesinlms.course.speakers.page_view"
    COURSE_BOOKMARKS_VIEW = "kinesinlms.course.bookmarks.page_view"
    COURSE_FORUM_TOPICS_VIEW = "kinesinlms.course.forum_topics.page_view"
    # Someone performed a search
    COURSE_SEARCH_REQUEST = "kinesinlms.course.search.search_request"

    COURSE_PAGE_VIEW = "kinesinlms.course.content.page_view"

    BOOKMARK_CREATED = "kinesinlms.course.bookmark.created"
    BOOKMARK_DELETED = "kinesinlms.course.bookmark.deleted"

    # RESOURCE EVENTS
    COURSE_RESOURCE_DOWNLOAD = "kinesinlms.course.resource.download"
    COURSE_BLOCK_RESOURCE_DOWNLOAD = "kinesinlms.course.resource.download"

    # ASSESSMENTS EVENTS
    COURSE_ASSESSMENT_ANSWER_SUBMITTED = "kinesinlms.course.assessment.submitted"

    # SIMPLE INTERACTIVE TOOL EVENTS
    COURSE_SIMPLE_INTERACTIVE_TOOL_SUBMITTED = "kinesinlms.course.simple_interactive_tool.submitted"

    # VIDEO EVENTS
    COURSE_VIDEO_ACTIVITY = "kinesinlms.course.video.activity"

    # FORUM EVENTS
    # TODO: Figure out how to capture Discourse Activity
    # TODO: and then log an event for each type we want to capture
    FORUM_POST = 'kinesinlms.course.forum.post'

    # PROGRESS
    MILESTONE_COMPLETED = "kinesinlms.course.progress.milestone.completed"
    MILESTONE_PROGRESSED = "kinesinlms.course.progress.milestone.progressed"
    COURSE_PASSED = "kinesinlms.course.progress.passed"
    COURSE_CERTIFICATE_EARNED = "kinesinlms.course.progress.certificate.earned"

    # This badge event can represent any BadgeClassType
    COURSE_BADGE_EARNED = "kinesinlms.course.progress.badge.earned"

    # OTHER ADMIN EVENTS
    ADMIN_KINESINLMS_TRAINER_FORM_SUBMITTED = "kinesinlms.site.trainer.trainer_form_submitted"

    # SURVEY
    SURVEY_COMPLETED = "kinesinlms.survey.completed"

    # COURSE ADMIN
    COURSE_ADMIN_PAGE_VIEW = "kinesinlms.course.admin.page_view"
    COURSE_ADMIN_COHORT_CREATED = "kinesinlms.course.admin.cohort_created"
    COURSE_ADMIN_COHORT_MEMBERSHIP_MODIFIED = "kinesinlms.course.admin.cohort_membership_modified"

    COURSE_ADMIN_REPORT_GENERATED = "kinesinlms.course.admin.report_generated"
    COURSE_ADMIN_DOWNLOAD = "kinesinlms.course.admin.download"

    # ~~~~~~~~~~~~~~~~~~~~~
    # EVENT_DATA TYPES
    # ~~~~~~~~~~~~~~~~~~~~~

    # These event types appear in the event_data section of an event

    # Course Video Event
    # These appear in the event_data section of a COURSE_VIDEO_ACTIVITY event
    COURSE_VIDEO_LOAD = "kinesinlms.course.video.load"
    COURSE_VIDEO_PLAY = "kinesinlms.course.video.play"
    COURSE_VIDEO_PAUSE = "kinesinlms.course.video.pause"
    COURSE_VIDEO_END = "kinesinlms.course.video.end"
    COURSE_VIDEO_ERROR = "kinesinlms.course.video.error"
    COURSE_VIDEO_REPLAY_CLICKED = "kinesinlms.course.video.replay_clicked"
    COURSE_VIDEO_PLAYBACK_RATE_CHANGE = "kinesinlms.course.video.playback_rate_change"
    COURSE_VIDEO_PLAYBACK_QUALITY_CHANGE = "kinesinlms.course.video.playback_quality_change"


ALL_VALID_EVENTS = [event.value for event in TrackingEventType]
ALL_VALID_VIDEO_EVENTS = [
    TrackingEventType.COURSE_VIDEO_LOAD.value,
    TrackingEventType.COURSE_VIDEO_PLAY.value,
    TrackingEventType.COURSE_VIDEO_PAUSE.value,
    TrackingEventType.COURSE_VIDEO_END.value,
    TrackingEventType.COURSE_VIDEO_ERROR.value,
    TrackingEventType.COURSE_VIDEO_PLAYBACK_RATE_CHANGE.value,
    TrackingEventType.COURSE_VIDEO_PLAYBACK_QUALITY_CHANGE.value,
    TrackingEventType.COURSE_VIDEO_REPLAY_CLICKED.value
]

# These events are tracked even after a course finishes...
POST_COURSE_TRACKED_EVENTS = [
    TrackingEventType.COURSE_CUSTOM_APP_PAGE_VIEW.value,
    TrackingEventType.COURSE_EXTRA_PAGE_VIEW.value,
    TrackingEventType.COURSE_HOME_VIEW.value,
    TrackingEventType.COURSE_PROGRESS_VIEW.value,
    TrackingEventType.COURSE_CERTIFICATE_VIEW.value,
    TrackingEventType.COURSE_SPEAKERS_VIEW.value,
    TrackingEventType.COURSE_BOOKMARKS_VIEW.value,
    TrackingEventType.COURSE_FORUM_TOPICS_VIEW.value,
    TrackingEventType.COURSE_SEARCH_REQUEST.value,
    TrackingEventType.COURSE_PAGE_VIEW.value,
    TrackingEventType.BOOKMARK_CREATED.value,
    TrackingEventType.COURSE_RESOURCE_DOWNLOAD.value,
    TrackingEventType.COURSE_BLOCK_RESOURCE_DOWNLOAD.value,
    TrackingEventType.COURSE_VIDEO_ACTIVITY.value,
    TrackingEventType.COURSE_ADMIN_PAGE_VIEW.value,
    TrackingEventType.COURSE_ADMIN_COHORT_CREATED.value,
    TrackingEventType.COURSE_ADMIN_COHORT_MEMBERSHIP_MODIFIED.value,
    TrackingEventType.COURSE_ADMIN_REPORT_GENERATED.value,
    TrackingEventType.COURSE_ADMIN_DOWNLOAD.value
]

# Events where it's ok if the user is not logged in and therefore 'anonymous'
ANON_USER_VALID_EVENTS = [
    TrackingEventType.ADMIN_KINESINLMS_TRAINER_FORM_SUBMITTED.value
]

# By default, the event string for an event relevant to a course is
# prefixed with the course token.
# e.g. DEMO_SP:kinesinlms.course.video.play

# Events not related to a specific course do not get a course prefix.
# The events listed below are **not** prefixed.
NON_PREFIXED_EVENTS = [
    TrackingEventType.USER_REGISTRATION.value,
    TrackingEventType.USER_EMAIL_CONFIRMED.value,
    TrackingEventType.USER_EMAIL_AUTOMATION_PROVIDER_USER_ID_CREATED.value,
    TrackingEventType.USER_LOGIN.value,
    TrackingEventType.ADMIN_KINESINLMS_TRAINER_FORM_SUBMITTED.value
]

TRACKING_EVENT_HELP_TEXT = {
    TrackingEventType.USER_REGISTRATION.name: _("A user has registered on the course site."),
    TrackingEventType.USER_EMAIL_CONFIRMED.name: _(
        "A user has clicked the confirmation link in the 'email confirmation' "
        "email KinesinLMS sends after a user fills out the registration form."),
    TrackingEventType.ENROLLMENT_ACTIVATED.name: _("A user has enrolled in this course."),
    TrackingEventType.ENROLLMENT_DEACTIVATED.name: _("A user has unenrolled from this course."),
    TrackingEventType.COURSE_CERTIFICATE_EARNED.name: _("A user has earned a completion certificate for this course."),

}
