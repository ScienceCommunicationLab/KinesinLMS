import typing

from django.shortcuts import render

from kinesinlms.badges.models import BadgeAssertion

help_topics = [
    {
        "slug": "intro",
        "title": "Introduction"
    },
    {
        "slug": "badges",
        "title": "Badges"
    },
    {
        "slug": "interactive_tools",
        "title": "Interactive Course Tools",
        "subtopics": [
            {

                "title": "How to use the 'Table Tool'",
                "slug": "tabletool"
            },
            {
                "slug": "diagramtool",
                "title": "How to use the 'Diagram Tool'"
            }
        ]
    }
]


def build_help_page_lookup(obj: typing.Any,
                           lookup: typing.Dict,
                           count: int = 1):
    if isinstance(obj, list):
        count = 1
        for item in obj:
            build_help_page_lookup(item, lookup, count)
            count += 1
    else:
        obj['count'] = count
        slug = obj['slug']
        lookup[slug] = obj
        for subtopic in obj.get('subtopics', {}):
            build_help_page_lookup(subtopic, lookup)
            subtopic['parent'] = obj
    return lookup


help_page_lookup = build_help_page_lookup(help_topics, {})


def help_main_page(request):
    template_name = "help/main.html"
    context = {
        "title": "Help",
        "description": "Help resources for KinesinLMS",
        "help_topics": help_topics
    }
    return render(request, template_name, context)


def help_page(request, help_page_slug: str):
    """
    Show a page from the help section.
    """

    template_name = f"help/{help_page_slug}.html"
    help_topic = help_page_lookup.get(help_page_slug, None)

    breadcrumbs = [
        {
            "url": "/help",
            "label": "Help"
        }
    ]

    help_topic_slug = None
    help_topic_id = None
    if help_topic:
        help_topic_slug = help_topic['slug']
        help_topic_id = help_topic['count']
        parent = help_topic.get('parent', None)
        if parent:
            help_topic_id = f"{parent['count']}.{help_topic_id}"
        else:
            help_topic_id = f"{help_topic_id}."

    context = {
        "title": "Help",
        "description": "Help resources for KinesinLMS",
        "breadcrumbs": breadcrumbs,
        "help_topics": help_topics,
        "help_topic": help_topic,
        "active_topic_slug": help_topic_slug,
        "help_topic_id": help_topic_id
    }

    # handle custom data for relevant pages
    badge_assertion_id = request.GET.get('badge_assertion_id', None)
    if help_page_slug == 'badges' and badge_assertion_id:
        badge_assertion = BadgeAssertion.objects.get(id=badge_assertion_id)
        if badge_assertion.recipient == request.user:
            context['badge_assertion'] = badge_assertion

    return render(request, template_name, context)
