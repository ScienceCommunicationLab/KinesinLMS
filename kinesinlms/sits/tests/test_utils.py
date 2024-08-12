from dataclasses import dataclass
from typing import Union
from unittest import TestCase

from kinesinlms.sits.utils import get_static_view_of_tabletool


@dataclass()
class DummySit:
    tool_type: str
    definition: Union[list, dict]


@dataclass()
class DummySitAnswer:
    json_content: Union[list, dict]


class TestGetStaticViewOfTableTool(TestCase):

    def test_merges_default_values_with_submission_values_correctly(self):
        sit = DummySit(
            tool_type='TABLETOOL',
            definition={
                "column_definitions": [
                    {
                        "header": "Potential Roles of a Primary Research Advisor",
                        "column_id": "role_of_advisor",
                        "default_cell_type": "USER_ENTRY"
                    },
                    {
                        "header": "My Role Priorities",
                        "column_id": "my_role_priorities",
                        "default_cell_type": "USER_ENTRY"
                    }
                ],
                "default_rows": [
                    {
                        "cells": [
                            {
                                "cell_type": "STATIC",
                                "column_id": "role_of_advisor",
                                "default_value": "<p><strong>Developing as a Researcher</strong></p><p>Mentors who help me:</p>"
                            },
                            {
                                "cell_type": "STATIC",
                                "column_id": "my_role_priorities",
                                "default_value": " "
                            }
                        ],
                        "row_id": 1
                    },
                    {
                        "cells": [
                            {
                                "cell_type": "USER_ENTRY",
                                "column_id": "role_of_advisor",
                                "default_value": "Some default content"
                            },
                            {
                                "cell_type": "USER_ENTRY",
                                "column_id": "my_role_priorities",
                                "default_value": "Some more default content"
                            }
                        ],
                        "row_id": 7
                    },

                ],

            }
        )
        sit_answer = DummySitAnswer(
            json_content=[
                {
                    "cells": [
                        {
                            "value": "some student answer for 'disciplinary knowledge and skills'",
                            "column_id": "my_role_priorities"
                        }
                    ],
                    "row_id": 4
                },
                {
                    "cells": [
                        {
                            "value": "an example student answer\n\non multiple lines for 'maintaining health and well-being' row",
                            "column_id": "my_role_priorities"
                        }
                    ],
                    "row_id": 7
                },
                {
                    "cells": [
                        {
                            "value": "an example student answer on new row' row",
                            "column_id": "my_role_priorities"
                        }
                    ],
                    "row_id": 8
                }
            ]
        )

        static_view = get_static_view_of_tabletool(sit, sit_answer)

        self.maxDiff = None

        expected_dict = {
            "header_columns": [
                {
                    "name": "Potential Roles of a Primary Research Advisor"
                },
                {
                    "name": "My Role Priorities"
                }
            ],
            "rows": [
                {
                    "cells": [
                        {
                            "content": "<p><strong>Developing as a Researcher</strong></p><p>Mentors who help me:</p>"
                        },
                        {
                            "content": " "
                        }
                    ],
                },
                {
                    "cells": [
                        {
                            "content": ""
                        },
                        {
                            "content": ""
                        }
                    ]
                },
                {
                    "cells": [
                        {
                            "content": ""
                        },
                        {
                            "content": ""
                        }
                    ]
                },
                {
                    "cells": [
                        {
                            "content": ""
                        },
                        {
                            "content": "some student answer for 'disciplinary knowledge and skills'"
                        }
                    ]
                },
                {
                    "cells": [
                        {
                            "content": ""
                        },
                        {
                            "content": ""
                        }
                    ]
                },
                {
                    "cells": [
                        {
                            "content": ""
                        },
                        {
                            "content": ""
                        }
                    ]
                },
                {
                    "cells": [
                        {
                            "content": "Some default content"
                        },
                        {
                            "content": "an example student answer\n\non multiple lines for 'maintaining health and well-being' row"
                        }
                    ]
                },
                {
                    "cells": [
                        {
                            "content": ""
                        },
                        {
                            "content": "an example student answer on new row' row"
                        }
                    ],
                },
            ]
        }

        self.assertEqual(
            static_view,
            expected_dict
        )

    def test_ignores_other_sits(self):
        sit = DummySit(
            tool_type='DIAGRAMTOOL',
            definition={},
        )
        sit_answer = DummySitAnswer(
            json_content=[],
        )

        static_view = get_static_view_of_tabletool(sit, sit_answer)

        self.assertIsNone(static_view)
