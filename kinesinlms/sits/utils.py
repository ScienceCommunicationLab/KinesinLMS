from kinesinlms.sits.constants import SimpleInteractiveToolType
from kinesinlms.sits.models import SimpleInteractiveTool, SimpleInteractiveToolSubmission


# noinspection PyUnresolvedReferences
def get_static_view_of_tabletool(sit: SimpleInteractiveTool,
                                 sit_answer: SimpleInteractiveToolSubmission = None):
    """
    Combines a tabletool definition and a student answer into a simple
    dictionary structure for the whole table.

    If sit_answer is None, the table is rendered in basic 'unanswered' form
    (e.g. for a course outline).

        {
            "header_columns": [ { "name": "" } ],
            "rows": [
                ... one dictionary for each row...
                {
                    "cells: [
                        ... one dictionary for each cell...
                        { "content": "" }
                    ]
                }
            ]
        }

    Args:
        sit:            Instance of a SimpleInteractiveTool type 'TABLETOOL'
        sit_answer:     (Optional) instance of a SimpleInteractiveToolSubmission
                        representing a student's input to this table

    Returns:
        Dictionary with content in the form described above,
        or `None` if the given sit is not a TABLETOOL type of SimpleInteractiveTool
        or does not have a definition.
    """
    if sit.tool_type != SimpleInteractiveToolType.TABLETOOL.name:
        return None
    if not sit.definition:
        return None

    header_ids = list(
        map(lambda col_def: col_def.get('column_id'), sit.definition.get('column_definitions', [])))
    header_columns = list(
        map(lambda col_def: {"name": col_def.get('header')}, sit.definition.get('column_definitions', [])))

    default_rows = sit.definition.get('default_rows', list())

    answers_rows = []
    if sit_answer:
        answers_rows = sit_answer.json_content or list()

    # Determine max row id
    max_row_id = 0
    if default_rows or answers_rows:
        max_default_row_ids = [row.get('row_id', 0) for row in default_rows]
        max_answer_row_ids = [row.get('row_id', 0) for row in answers_rows]
        max_row_id = max(max_default_row_ids + max_answer_row_ids)

    rows = []
    if max_row_id == 0:
        # Create a blank row to give table a bit more shape
        blank_row = {
            "cells": []
        }
        for column_id in header_ids:
            blank_row['cells'].append({
                "content": " \n "
            })
        rows.append(blank_row)
    else:
        # add in each row that has default and/or user content
        for row_id in range(1, max_row_id + 1):
            row = {
                "cells": []
            }
            default_columns = next(
                iter(filter(lambda default_row: default_row.get('row_id', 0) == row_id, default_rows)),
                dict()
            ).get('cells', list())
            columns = next(
                iter(filter(lambda answer_row: answer_row.get('row_id', 0) == row_id, answers_rows)),
                dict()
            ).get('cells', list())

            cells = []
            for column_id in header_ids:
                content = None
                default_value_cell = next(
                    iter(filter(lambda default_col: default_col.get('column_id') == column_id, default_columns)),
                    None
                )
                if default_value_cell is not None:
                    content = default_value_cell.get('default_value', '')
                value_cell = next(
                    iter(filter(lambda col: col.get('column_id') == column_id, columns)),
                    None
                )
                if value_cell is not None:
                    content = value_cell.get('value', '')
                cells.append({'content': content or ''})

            row['cells'] = cells
            rows.append(row)

    return {
        'header_columns': header_columns,
        'rows': rows,
    }
