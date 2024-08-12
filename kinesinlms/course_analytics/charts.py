from dataclasses import dataclass
from datetime import timedelta
from typing import List, Optional

import pandas as pd
from django.db.models import Count, Q
from django.utils import timezone
from django_pandas.io import read_frame

from kinesinlms.core.styles import event_colors, rand_color
from kinesinlms.course.models import Course, Cohort
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.models import TrackingEvent


@dataclass
class BasicChartData:
    label: str
    data: List
    bar_color: str = '#000000'


@dataclass
class BasicChart:
    slug: str
    start_datetime: str
    end_datetime: str
    graph_data: List[BasicChartData]
    legend_position: Optional[str] = None


def bar_color_for_event_type(event_type):
    if event_type in event_colors:
        color = event_colors[event_type]
        return color
    else:
        new_color = rand_color()
        event_colors[event_type] = new_color
        return new_color


def get_engagement_chart(course: Course,
                         cohort: Cohort = None,
                         ignore_staff_data=True) -> Optional[BasicChart]:
    """
    Builds up a BasicChart dataclass instance to represent
    engagement for given course and cohort.


    returns:
        BasicChart instance, or None if no data.

    """

    end_datetime = timezone.now().date() + timedelta(days=1)
    start_datetime = end_datetime + timedelta(days=-90)

    graph_data = []
    basic_chart = BasicChart(slug='engagement-chart',
                             start_datetime=start_datetime,
                             end_datetime=end_datetime,
                             graph_data=graph_data,
                             legend_position='right')

    engagement_event_types = [
        TrackingEventType.COURSE_PAGE_VIEW.value,
        TrackingEventType.COURSE_VIDEO_ACTIVITY.value,
        TrackingEventType.FORUM_POST.value,
        TrackingEventType.COURSE_ASSESSMENT_ANSWER_SUBMITTED.value,
        TrackingEventType.COURSE_SIMPLE_INTERACTIVE_TOOL_SUBMITTED.value
    ]

    qs = TrackingEvent.objects.filter(course_run=course.run,
                                      course_slug=course.slug,
                                      time__range=[start_datetime, end_datetime],
                                      event_type__in=engagement_event_types)

    if cohort:
        cohort_users = cohort.students.all()
        qs = qs.filter(user__in=cohort_users)

    if ignore_staff_data:
        qs = qs.filter(Q(user__is_staff=False) & Q(user__is_test_user=False))

    if qs.count() == 0:
        return None

    df = read_frame(qs)
    df = df[['time', 'event_type']]
    df = df.set_index('time')
    df = pd.get_dummies(df)
    df = df.resample('D').sum()

    for event_type in engagement_event_types:
        event_data = []
        # Columns got prefixed when we called get_dummies(). Adjust accordingly...
        column_name = f"event_type_{event_type}"
        if column_name not in df.columns:
            continue
        event_df = df[[column_name]]
        for index, row in event_df.iterrows():
            d = {
                'x': index.strftime('%Y-%m-%d'),
                'y': row.get(column_name, 0)
            }
            event_data.append(d)
        chart_label = TrackingEventType(event_type).name
        graph_data = BasicChartData(label=chart_label,
                                    data=event_data,
                                    bar_color=bar_color_for_event_type(event_type))
        basic_chart.graph_data.append(graph_data)

    return basic_chart


def get_course_passed_chart(course: Course,
                            cohort: Cohort = None,
                            ignore_staff_data=True,
                            bar_color="#D95953") -> Optional[BasicChart]:
    """
    Builds up a BasicChart dataclass instance to represent
    course passed status for given course and cohort.


    returns:
        BasicChart instance, or None if no data.
    """

    end_datetime = timezone.now().date() + timedelta(days=1)
    start_datetime = end_datetime + timedelta(days=-90)
    graph_data = []
    basic_chart = BasicChart(start_datetime=start_datetime,
                             end_datetime=end_datetime,
                             graph_data=graph_data,
                             slug='course-passed-chart')
    qs = TrackingEvent.objects.filter(course_run=course.run,
                                      course_slug=course.slug,
                                      time__range=[start_datetime, end_datetime],
                                      event_type=TrackingEventType.COURSE_PASSED.value)

    qs = qs.extra(select={'created_date': "date(time)"}) \
        .values('created_date') \
        .order_by('created_date') \
        .annotate(y=Count('id')).all()

    if cohort:
        cohort_users = cohort.students.all()
        qs = qs.filter(user__in=cohort_users)

    if ignore_staff_data:
        qs = qs.filter(Q(user__is_staff=False) & Q(user__is_test_user=False))

    if qs.count() == 0:
        return None

    course_passeds = list(qs)

    course_passed_data = [{'x': item['created_date'].strftime('%Y-%m-%d'), 'y': item['y']} for item in course_passeds]
    data = BasicChartData(label="Course Passed",
                          bar_color=bar_color,
                          data=course_passed_data)

    basic_chart.graph_data = [data]

    return basic_chart


def get_enrollments_chart(course: Course,
                          cohort: Cohort = None,
                          ignore_staff_data=True,
                          bar_color="#D95953") -> Optional[BasicChart]:
    """
    Builds up a BasicChart dataclass instance to represent
    enrollments for given course and cohort.


    returns:
        BasicChart instance, or None if no data.
    """

    end_datetime = timezone.now().date() + timedelta(days=1)
    start_datetime = end_datetime + timedelta(days=-90)
    graph_data = []
    basic_chart = BasicChart(start_datetime=start_datetime,
                             end_datetime=end_datetime,
                             graph_data=graph_data,
                             slug='enrollments-chart')
    qs = TrackingEvent.objects.filter(course_run=course.run,
                                      course_slug=course.slug,
                                      time__range=[start_datetime, end_datetime],
                                      event_type=TrackingEventType.ENROLLMENT_ACTIVATED.value)

    qs = qs.extra(select={'created_date': "date(time)"}) \
        .values('created_date') \
        .order_by('created_date') \
        .annotate(y=Count('id')).all()

    if cohort:
        cohort_users = cohort.students.all()
        qs = qs.filter(user__in=cohort_users)

    if ignore_staff_data:
        qs = qs.filter(Q(user__is_staff=False) & Q(user__is_test_user=False))

    if qs.count() == 0:
        return None

    enrollments = list(qs)

    enrollments_data = [{'x': item['created_date'].strftime('%Y-%m-%d'), 'y': item['y']} for item in enrollments]
    data = BasicChartData(label="Enrollments", data=enrollments_data, bar_color=bar_color)

    basic_chart.graph_data = [data]

    return basic_chart
