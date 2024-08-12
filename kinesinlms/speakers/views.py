from django.shortcuts import render, get_object_or_404

from kinesinlms.speakers.models import Speaker


def speakers_list(request):
    """
    Show a list of speakers

    Args:
        request (_type_): _description_

    Returns:
        _type_: _description_
    """

    speakers = Speaker.objects.all().order_by('last_name')

    context = {
        "section": "speakers",
        "title": "Course Speakers",
        "description": "A list of all speakers appearing in courses on KinesinLMS",
        "courses": speakers
    }

    return render(request, 'speakers/speakers_list.html', context)


def speaker_detail(request, speaker_slug):
    speaker = get_object_or_404(Speaker, slug=speaker_slug)

    context = {
        "section": "speakers",
        "breadcrumbs": [
            {
                "url": "/speakers",
                "label": "Course Speakers"
            }
        ],
        "title": "Speaker Bio",
        "description": f"A short biography of {speaker.full_name}",
        "speaker": speaker
    }

    return render(request, 'speakers/kinesinlms_speaker.html', context)
