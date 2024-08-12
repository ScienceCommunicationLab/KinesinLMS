# Event Tracking

## Event Tracking Requirements

A few simple requirements helped shape the way we're capturing and logging events.

1) Handle Client or Server Origin: Most of the events we need to track can be captured and handled on the server. But
   some we want to get directly from the client, for example video play and pause events from the YouTube player. So
   we've created an API endpoint for our client components to send tracking event data.

2) Delivery to 'Somewhere Else' for Handling: External services will want to do different things
   based on events (e.g. send email, send a message to slack, etc.), and we're going to expect that this logic
   lives somewhere else and not in the LMS. So we'll use Celery tasks to do async sends to...somewhere! You
   can extend the Tracker class to implement logic to send your event to an external service.

Note that events shouldn't contain personal information for a user. By convention, we only include the user's
anonymous ID.

## Tracking API endpoint

React components running in the client can send POST events to the `/api/tracking` endpoint to register events
originating on the client. There's no library yet so each component just constructs its own POST request
(See the VideoPlayer.tsx component for an example).

For example, for video events the JSON payload looks like this:

```
{
  "tracking_event_type": "video",
  "node_id": this.state.nodeID,
  "event_data": {
    "video_id": this.state.videoID,
    "video_event_type": videoEventType
  }
}
```

The `event_data` portion is the part that will change depending on the type of event. For video activity it's always
just the two properties you see above.

All validation of incoming events through the API is done by Django Rest Framework. Following best practice ('thick
serializers, thin views`), the serializer itself handles calling the Tracker rather than saving a model instance.
Perhaps in the future I'll refactor that logic into a helper class.

## Tracker Class

This class encapsulates the code necessary to send off an event to ... somewhere.

It provides one method, `track`, which should be called from wherever something interesting happens
that we want to track: a registration, an enrollment, an assessment entry, etc.

The `track` function takes the following arguments:

- `event_type` : An event type. Must be one of the constant strings defined in event_types.py
- `user` : A user object, perhaps pulled from the request or from a model class.
- `data` : A dictionary that takes on different properties depending on the `event_type`
- `course_content_node` : The course node this event took place in, if applicable (registration events don't have a
  course node).

## Event Structure

All events will have the following basic JSON shape.

```
{
    "event_type": (some event type)
    "anon_username": (anonymized username, from anon_username field in user model),
    "time": (format like 2014-03-03T16:19:05.584523+00:00)
    "course_slug": (course slug),
    "course_run": (run),
    "module_id": (module id),
    "section_id": (section id),
    "unit_id": (unit id),
    "page_url": (the page URL)
    "event_data": {
        (All data related to this event type. Structure depends on event type...see definitions below.)
    }

}
```

### time

This is the UTC time when the event was recorded. It will be in ‘YYYY-MM-DDThh:mm:ss.xxxxxx’ format.
