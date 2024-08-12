"""
Schema to define the json shape that is stored in
SimpleInteractiveTool's definition json field.

We used to use JSON schema but now using dataclasses with dataclasses_json
to provide us a more efficient way of defining expected
structure of json fields.

"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List

from dataclasses_json import dataclass_json, Undefined


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# DIAGRAM TOOL
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class DiagramTrayNodeType(Enum):
    GENERIC = "Generic"
    MENTOR_CATEGORY = "Mentor category"


@dataclass_json(undefined=Undefined.RAISE)
@dataclass
class DiagramToolDefinition:
    # props for all DIAGRAM types of SITs...
    tray_nodes_type: str = DiagramTrayNodeType.GENERIC.name
    tray_instructions: Optional[str] = None
    disable_link_strength: bool = False

    # props specific to MENTOR_CATEGORY tray_nodes_type...
    open_mentor_type_popup_after_add: bool = False
    can_save_without_mentor_type: bool = False


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# TABLE TOOL
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@dataclass_json(undefined=Undefined.RAISE)
@dataclass
class TableToolColumnDefinition:
    column_id: str
    default_cell_type: Optional[str] = None
    header: str = ""


@dataclass_json(undefined=Undefined.RAISE)
@dataclass
class TableToolCellDefinition:
    column_id: str
    # 'cell_type' is optional and should default to the type defined on the ColumnDefinition.
    cell_type: Optional[str] = None
    default_value: str = ""


@dataclass_json(undefined=Undefined.RAISE)
@dataclass
class TableToolRowDefinition:
    row_id: int
    cells: List[TableToolCellDefinition] = field(default_factory=list)


@dataclass_json(undefined=Undefined.RAISE)
@dataclass
class TableToolDefinition:
    column_definitions: List[TableToolColumnDefinition] = field(default_factory=list)
    default_rows: List[TableToolRowDefinition] = field(default_factory=list)

    allow_add_row: bool = False
    allow_remove_row: bool = False
    max_rows: int = 100
    initial_empty_rows: int = 3
