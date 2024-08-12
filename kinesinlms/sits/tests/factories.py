import logging

import factory

from kinesinlms.sits.models import SimpleInteractiveTool, SimpleInteractiveToolSubmission, \
    SimpleInteractiveToolType, SimpleInteractiveToolSubmissionStatus

logger = logging.getLogger(__name__)


class SimpleInteractiveToolFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SimpleInteractiveTool

    tool_type = SimpleInteractiveToolType.DIAGRAM.name
    slug = factory.Sequence(lambda n: f"simple-interactive-tool-{n}")
    definition = {}


# TODO: Currently test classes are using above SimpleInteractiveToolFactory
#   and expecting a DiagramTool. Update to use this class...
class DiagramtoolFactory(SimpleInteractiveToolFactory):
    tool_type = SimpleInteractiveToolType.DIAGRAM.name


class TabletoolFactory(SimpleInteractiveToolFactory):
    name = "Test Tabletool"
    tool_type = SimpleInteractiveToolType.TABLETOOL.name
    slug = "test-tabletool"
    instructions = "Here are some instructions."
    definition = {
        "default_rows": [
            {
                "cells": [
                    {
                        "cell_type": "STATIC",
                        "column_id": "goals",
                        "default_value": "Short-term"
                    },
                    {
                        "cell_type": "STATIC",
                        "column_id": "possible_mentors"
                    },
                    {
                        "cell_type": "STATIC",
                        "column_id": "more_mentorship"
                    }
                ],
                "row_id": 1
            },
            {
                "cells": [
                    {
                        "cell_type": "USER_ENTRY",
                        "column_id": "goals",
                        "default_value": "1"
                    }
                ],
                "row_id": 2
            },
            {
                "cells": [
                    {
                        "cell_type": "USER_ENTRY",
                        "column_id": "goals",
                        "default_value": "2"
                    }
                ],
                "row_id": 3
            },
            {
                "cells": [
                    {
                        "cell_type": "USER_ENTRY",
                        "column_id": "goals",
                        "default_value": "3"
                    }
                ],
                "row_id": 4
            },
            {
                "cells": [
                    {
                        "cell_type": "USER_ENTRY",
                        "column_id": "goals",
                        "default_value": "4"
                    }
                ],
                "row_id": 5
            },
            {
                "cells": [
                    {
                        "cell_type": "USER_ENTRY",
                        "column_id": "goals",
                        "default_value": "5"
                    }
                ],
                "row_id": 6
            },
            {
                "cells": [
                    {
                        "cell_type": "USER_ENTRY",
                        "column_id": "goals",
                        "default_value": "6"
                    }
                ],
                "row_id": 7
            },
            {
                "cells": [
                    {
                        "cell_type": "STATIC",
                        "column_id": "goals",
                        "default_value": "Long-term"
                    },
                    {
                        "cell_type": "STATIC",
                        "column_id": "possible_mentors"
                    },
                    {
                        "cell_type": "STATIC",
                        "column_id": "more_mentorship"
                    }
                ],
                "row_id": 8
            },
            {
                "cells": [
                    {
                        "cell_type": "USER_ENTRY",
                        "column_id": "goals",
                        "default_value": "1"
                    }
                ],
                "row_id": 9
            },
            {
                "cells": [
                    {
                        "cell_type": "USER_ENTRY",
                        "column_id": "goals",
                        "default_value": "2"
                    }
                ],
                "row_id": 10
            },
            {
                "cells": [
                    {
                        "cell_type": "USER_ENTRY",
                        "column_id": "goals",
                        "default_value": "3"
                    }
                ],
                "row_id": 11
            }
        ],
        "allow_add_row": False,
        "allow_remove_row": False,
        "column_definitions": [
            {
                "header": "Goals",
                "column_id": "goals",
                "default_cell_type": "USER_ENTRY"
            },
            {
                "header": "Possible Mentors",
                "column_id": "possible_mentors",
                "default_cell_type": "USER_ENTRY"
            },
            {
                "header": "Do you need more mentorship?",
                "column_id": "more_mentorship",
                "default_cell_type": "USER_ENTRY"
            }
        ]
    }
    graded = True


class SimpleInteractiveToolSubmissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SimpleInteractiveToolSubmission

    status = SimpleInteractiveToolSubmissionStatus.UNANSWERED.name
    json_content = {
        "answer": "Some answer text."
    }
