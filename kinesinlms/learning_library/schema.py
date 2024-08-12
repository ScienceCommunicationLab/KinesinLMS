# JSON Schema to validate JSON fields in course models
from .constants import CalloutType

# ================================
# JSON SCHEMA
# ================================

# These schema describe the shape of the json_content
# stored in various models, such as Block Models or models that provide
# extra data for the block, such as Assessment or SimpleInteractiveTool.

# This information is stored as JSON rather than relational models
# as it's assumed in these cases the data is too variable to be
# easily modeled in a relational way.

# That could be complete bunk and using JSON with schema validation
# in these places is so misguided, you've lost your appetite for lunch.
# If so, help us make it better.

# Until then, the schema below are used to validate incoming JSON via the
# API or via a Django form.

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Schema for BLOCK model json
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# These schema describe the shape of the json_content
# stored in Block objects.

ANSWER_LIST_BLOCK_SCHEMA = {
    "type": "object",
    "properties": {
        "unit_block_slugs": {
            "type": "array",
            "minItems": 0,
            "maxItems": 100,
            "items": {
                "type": "string"
            }
        }
    },
    "required": ['unit_block_slugs']
}

CALLOUT_BLOCK_SCHEMA = {
    "type": "object",
    "properties": {
        "callout_type": {
            "type": "string",
            "enum": CalloutType.get_callout_types()
        },
        "link_title": {
            "type": "string"
        },
        "link_url": {
            "type": "string",
        }
    },
    "required": ["callout_type"],
    "additionalProperties": False,
}

HTML_CONTENT_BLOCK_SCHEMA = {
    "type": object,
    "properties": {
        "sidebar_content": {"type": "string"}
    },
    "additionalProperties": False
}

SURVEY_BLOCK_SCHEMA = {
    "type": "object",
    "properties": {
        "survey_id": {"type": "string"},
        "survey_type": {"type": "string"},
        "sidebar_content": {"type": "string"}
    },
    "required": ["survey_type"],
    "additionalProperties": False,
}

VIDEO_BLOCK_SCHEMA = {
    "type": "object",
    "properties": {
        "header": {"type": "string"},
        "video_id": {"type": "string"},
        "player_type": {"type": "string"}
    },
    "required": ["header", "video_id"],
    "additionalProperties": False,
}

# A VIDEO_BLOCK object Looks like this:
"""
{
    "header": "blah blah",
    "video_id": "asdjfklsjaf"
}
"""
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Schema for ASSESSMENT model json
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Assessments have two json fields: definition_json and solution_json
# The definition_json field is used to store the definition of the assessment
# but not any data about the correct solution. This allows definition json
# to be shared with rich clients, if necessary, without revealing the correct solution.

# LONG_FORM_TEXT_SCHEMA NOT NEEDED YET. NO USE OF JSON_CONTENT IN ASSESSMENT OBJECT
# LONG_FORM_TEXT_SCHEMA = {}

DONE_INDICATOR_DEFINITION_SCHEMA = {
    "done_indicator_label": {"type": "string"}
}

POLL_DEFINITION_SCHEMA = {
    "type": "object",
    "properties": {
        "choices": {
            "type": "array",
            "minItems": 2,
            "maxItems": 20,
            "items": {
                "type": "object",
                "properties": {
                    "choice_key": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["text", "choice_key"],
                "additionalProperties": False,
            }
        }
    },
    "required": ["choices"],
    "additionalProperties": False,
}

# An example POLL_BLOCK object Looks like this:
"""
{
    "choices": [
        {
            "text": "First option is blah.",
            "choice_key": "a"
        },
        {
            "text": "Second option is meh.",
            "choice_key": "b"
        }
    ]
}
"""

# At the moment, multiple choice is exactly like poll (since we hold
# true/value state in solution_json property)
MULTIPLE_CHOICE_DEFINITION_SCHEMA = {
    "type": "object",
    "properties": {
        "choices": {
            "type": "array",
            "minItems": 2,
            "maxItems": 20,
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "choice_key": {"type": "string"},
                },
                "required": ["text", "choice_key"],
                "additionalProperties": False,
            }
        }
    },
    "required": ["choices"],
    "additionalProperties": False,
}


# An example MULTIPLE_CHOICE_BLOCK object Looks like this:
"""
{
    "choices": [
        {
            "text": "Here's a first option.",
            "choice_key": "a"
        },
        {
            "text": "Here's a second option.",
            "choice_key": "b"
        },
        {
            "text": "Here's a third option.",
            "choice_key": "c"
        }
    ]
}
"""

MULTIPLE_CHOICE_SOLUTION_SCHEMA = {
    "type": "object",
    "properties": {
        "correct_choice_keys": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "string"
            }
        },
        "join": {
            "type": "string",
            "enum": ["AND", "OR"]
        }
    },
    "required": ["correct_choice_keys"],
    "additionalProperties": False,
}
# An example MULTIPLE_CHOICE_BLOCK_CORRECT object Looks like this:
"""
{ 
    "correct_choice_keys": ["a", "b"], 
    "join": "AND" 
}
"""

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Schema for ANSWER models
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# These schema describe the shape of the json_content
# in the Answer model. Each type of assessment will
# product answer json with a particular shape.
# Incoming answer JSON via the api should be validated
# using these schema.

DONE_INDICATOR_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "boolean"
        }
    },
    "required": ["answer"]
}

MULTIPLE_CHOICE_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "minItems": 1,
        }
    },
    "required": ["answer"],
}

POLL_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "minItems": 0,
        }
    },
    "required": ["answer"],
}

LONG_FORM_TEXT_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string"
        }
    },
    "required": ["answer"]
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Schema for SIMPLE_INTERACTIVE_TOOL
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# SIT block types don't really store info in the Block json_content
# field...instead we use the definition json field on the
# SimpleInteractiveTool model. So the schema here -- which
# is for the actual Block model -- doesn't do anything, at least
# yet. In the future we may store some high-level info common to
# all SIT blocks.

SIMPLE_INTERACTIVE_TOOL_BLOCK_SCHEMA = None
