"""
Constant values for Simple Interactive Tool models and such.
"""
from enum import Enum

DEFAULT_MAX_TABLETOOL_ROWS_ALLOWED = 100


class TableToolCellType(Enum):
    STATIC = "Static"
    USER_ENTRY = "User entry"


class SimpleInteractiveToolMode(Enum):
    BASIC = "Basic"
    TEMPLATE = "Template"


class SimpleInteractiveToolType(Enum):
    DIAGRAM = "Diagram"
    TABLETOOL = "TableTool"


class SimpleInteractiveToolSubmissionStatus(Enum):
    UNANSWERED = 'Unanswered'
    INCOMPLETE = 'Incomplete'
    COMPLETE = 'Complete'
