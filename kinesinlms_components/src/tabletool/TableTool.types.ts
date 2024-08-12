/**
 * SERVER TYPES
 */
import { ReactElement } from 'react';

export interface TableToolDefinition {
    column_definitions: TableToolColumnDefinition[];
    default_rows: TableToolRowDefinition[];
    allow_add_row: boolean;
    allow_remove_row: boolean;
    max_rows: number;
    initial_empty_rows: number;
}

export type TableToolCellType =
    | "STATIC"
    | "USER_ENTRY"
    // 'Delete' is only added on the client.
    | "DELETE";

export interface TableToolColumnDefinition {
    column_id: string;
    default_cell_type: TableToolCellType;
    header: string;
}

export interface TableToolRowDefinition {
    row_id: number;
    cells: TableToolCellDefinition[];
}

export interface TableToolCellDefinition {
    column_id: string;
    cell_type?: TableToolCellType;
    default_value: string;
}

export interface TableToolSubmissionCell {
    column_id: string;
    value: string;
}

export interface TableToolSubmissionRow {
    row_id: number;
    cells: TableToolSubmissionCell[];
}

/**
 * CLIENT TYPES
 */

export interface Header {
    columnId: string;
    value: string;
}

export interface Row {
    rowId: number;
    cells: Cell[];
}

export interface Cell {
    columnId: string;
    render: () => ReactElement;
}
