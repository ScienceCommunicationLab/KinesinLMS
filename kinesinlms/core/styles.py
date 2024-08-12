import logging
import random
from typing import Dict

from kinesinlms.course.models import Course
from kinesinlms.survey.constants import SurveyType
from kinesinlms.tracking.event_types import TrackingEventType

logger = logging.getLogger(__name__)


def rand_color():
    def r() -> int:
        return random.randint(0, 255)

    new_color = ('#%02X%02X%02X' % (r(), r(), r()))
    return new_color


COURSE_COLORS = {}


def get_course_colors() -> Dict:
    if not bool(COURSE_COLORS):
        try:
            course_palette = ['#2fa3ee', '#4bcaad', '#86c157', '#d99c3f', '#ce6633', '#a35dd1']
            for course_index, course in enumerate(Course.objects.all()):
                try:
                    COURSE_COLORS[course.token] = course_palette[course_index]
                except IndexError:
                    COURSE_COLORS[course.token] = rand_color()
        except Exception as exc:
            logger.warning(f"Could not create course_colors. Error: {exc}")
    return COURSE_COLORS


# SET UP PALETTE FOR EVENTS WE CARE ABOUT GRAPHING
event_colors = {}
try:
    event_palette = ['#2da2bf', '#da1f28', '#eb641b', '#39639d', '#474b78', '#7d3c4a']
    events_needing_colors = [TrackingEventType.COURSE_PAGE_VIEW.value,
                             TrackingEventType.COURSE_ASSESSMENT_ANSWER_SUBMITTED.value,
                             TrackingEventType.COURSE_VIDEO_ACTIVITY.value,
                             TrackingEventType.COURSE_SIMPLE_INTERACTIVE_TOOL_SUBMITTED.value,
                             TrackingEventType.FORUM_POST.value]
    for index, event_name in enumerate(events_needing_colors):
        try:
            event_colors[event_name] = event_palette[index]
        except IndexError as ie:
            event_colors[event_name] = rand_color()
except Exception as e:
    logger.warning(f"Could not create event_colors. Error: {e}")

survey_colors = {}
try:
    survey_type_palette = ['#2da2bf', '#da1f28', '#eb641b']
    survey_types_needing_colors = [SurveyType.PRE_COURSE.name,
                                   SurveyType.POST_COURSE.name,
                                   SurveyType.FOLLOW_UP.name]
    for index, survey_type in enumerate(survey_types_needing_colors):
        try:
            survey_colors[survey_type] = survey_type_palette[index]
        except IndexError as ie:
            survey_colors[survey_type] = rand_color()
except Exception as e:
    logger.warning(f"Could not create survey_colors. Error: {e}")


def get_course_color(course_token: str) -> str:
    course_colors = get_course_colors()
    if course_token in course_colors:
        return course_colors[course_token]
    else:
        new_color = rand_color()
        course_colors[course_token] = new_color
        return rand_color()


def get_event_color(event_name: str) -> str:
    if event_name in event_colors:
        color = event_colors[event_name]
        return color
    else:
        new_color = rand_color()
        event_colors[event_name] = new_color
        return new_color


def get_survey_color(survey_type: str) -> str:
    if survey_type in survey_colors:
        color = survey_colors[survey_type]
        return color
    else:
        new_color = rand_color()
        event_colors[event_name] = new_color
        return new_color
