import { useEffect, useMemo, useRef } from 'react';
import { useState } from 'react';
import {
    Header,
    Row, TableToolCellType,
    TableToolColumnDefinition,
    TableToolRowDefinition, TableToolSubmissionCell,
    TableToolSubmissionRow
} from '../TableTool.types';
// @ts-ignore
import _ from 'lodash';
import getComponentForCellType from '../components/cells/getComponentForCellType';
// @ts-ignore
import jsonStableStringify from 'json-stable-stringify';

interface UseTableParams {
    columnDefinitions: TableToolColumnDefinition[];
    initialSubmissionRows: TableToolSubmissionRow[];
    defaultRows: TableToolRowDefinition[];
    minRows: number;
    maxRows: number;
    canAddRows: boolean;
    canRemoveRows: boolean;
    isReadOnly: boolean;
}

interface UseTableResult {
    headers: Header[];
    rows: Row[];
    submissionRows: TableToolSubmissionRow[];
    addEmptyRow: () => void;
    canAddEmptyRow: boolean;
    isDirty: boolean;
}

interface EnrichtedTableToolSubmissionRow extends TableToolSubmissionRow {
    // Some empty rows are added temporary, we keep that state to make sure they are not submitted.
    isEphemeral?: boolean;
}

export const DELETE_ROW_COLUMN_ID = 'DELETE_ROW_COLUMN_ID';

/**
 * This hook builds the object that represents all data visible in the table.
 * It merges default rows (that cannot be changed) with the rows (and cells)
 * already submitted and filled in by the user. The resulting and returned
 * data object is in the same format as the submission results.
 */
function useTable({
    columnDefinitions: _columnDefinitions,
    initialSubmissionRows: _initialSubmissionRows,
    defaultRows,
    minRows,
    maxRows,
    canAddRows,
    canRemoveRows,
    maxScore,
    isReadOnly,
}: UseTableParams): UseTableResult {
    const isEmptyCell = (cell: TableToolSubmissionCell) => {
        return !cell || !cell.value;
    }

    const initialSubmissionRows = _initialSubmissionRows.map(row => {
        // Exclude empty cells from the comparison, as an excluded cell and an empty cell are the same.
        return { ...row, cells: [...row.cells.filter(cell => !isEmptyCell(cell))] };
    });

    // Keep track of the initial (= non-saved) values to calculate the dirty state of the table.
    const initialSubmissionRowsRef = useRef(jsonStableStringify(initialSubmissionRows));
    useEffect(() => {
        initialSubmissionRowsRef.current = jsonStableStringify(initialSubmissionRows);
    }, [jsonStableStringify(initialSubmissionRows)]);

    // Keep the state of user entries. This will eventually be sent to the server.
    const [submissionRows, setSubmissionRows] = useState<EnrichtedTableToolSubmissionRow[]>(initialSubmissionRows);

    // Builds up the column definitions by using the ones that were passed and enriching them with others
    // like 'Delete' if those should be shown based on the context.
    const columnDefinitions = useMemo(() => {
        // Add the delete column if it should be there, but it actually is not.
        if (!isReadOnly && canRemoveRows && !_columnDefinitions.some(def => def.column_id === DELETE_ROW_COLUMN_ID)) {
            return [
                ..._columnDefinitions,
                {
                    column_id: DELETE_ROW_COLUMN_ID,
                    header: 'Delete',
                    default_cell_type: 'DELETE' as TableToolCellType,
                }
            ];
        }
        // Remove the delete column if it should not be there, but it actually is.
        if (isReadOnly || !canRemoveRows) {
            return [..._columnDefinitions.filter(def => def.column_id !== DELETE_ROW_COLUMN_ID)];
        }
        return [..._columnDefinitions];
    }, [jsonStableStringify(_columnDefinitions), isReadOnly, canRemoveRows]);

    const headers = columnDefinitions.map<Header>(def => ({
        value: def.header,
        columnId: def.column_id,
    }));
    // All columnIds, in the order they will appear in the UI.
    const columnIds = columnDefinitions.map(def => def.column_id);

    // Updates the value of one cell in the table.
    const updateValue = (rowId: number, columnId: string, value: string) => {
        const otherCellsInRow = (submissionRows.find(row => row.row_id === rowId)?.cells ?? [])
            .filter(cell => cell.column_id !== columnId);

        // Gather all the cells for the current row, included the cell with the updated value.
        const updatedCellsForRow: TableToolSubmissionCell[] = [
            ...otherCellsInRow,
            {
                column_id: columnId,
                value,
            }
        ];
        const updatedRow: TableToolSubmissionRow = {
            row_id: rowId,
            cells: updatedCellsForRow,
        };

        const updatedRows = [...submissionRows];


        const existingRowIndex = submissionRows.findIndex(row => row.row_id === updatedRow.row_id);
        const isNewValueEmpty = value === '' || value === undefined || value === null;

        if (existingRowIndex >= 0) {
            // The row already existed, so we can replace it.
            const oldValue = submissionRows[existingRowIndex].cells.find(cell => cell.column_id === columnId)?.value;
            const wasOldValueEmpty = oldValue === '' || oldValue === undefined || oldValue === null;
            // We do not update rows if the value changed from empty to... empty.
            // This usually means the user simple focused the input field, and went away.
            // This triggers an update of that field without value.
            if (wasOldValueEmpty && isNewValueEmpty) {
                return;
            }
            updatedRows.splice(existingRowIndex, 1, updatedRow);
        } else {
            // The row did not exist yet, so we can add it.
            // We only add a new row if the value is not empty.
            if (isNewValueEmpty) {
                return;
            }
            updatedRows.push(updatedRow);
        }

        setSubmissionRows(updatedRows);
    };

    // Delete a row if it is allowed.
    const deleteRow = (rowId: number) => {
        const isDefaultRow = defaultRows.find(row => row.row_id === rowId);
        // For now, it is not possible to delete a row with default values.
        if (!canRemoveRows || isDefaultRow) {
            return;
        }
        setSubmissionRows(prevRows => [...prevRows.filter(row => row.row_id !== rowId)]);
    };

    // Merge the default rows with the actual user-added rows and values to one flat list of rows.
    // This is the list that should be visible in the UI.
    const rows = useMemo(() => {
        const calculateCellType = (columnId: string, cellType?: TableToolCellType) => {
            const defaultCellType = columnDefinitions.find(def => def.column_id === columnId)?.default_cell_type;
            return cellType ?? defaultCellType ?? undefined;
        };

        const canDeleteRow = (rowId: number) => {
            return canRemoveRows && !defaultRows.map(row => row.row_id).includes(rowId);
        };

        const mappedDefaultRows = defaultRows.map<Row>(row => ({
            rowId: row.row_id,
            cells: row.cells.map(cell => ({
                columnId: cell.column_id,
                render: () => getComponentForCellType(
                    calculateCellType(cell.column_id, cell.cell_type),
                    isReadOnly,
                    {
                        rowId: row.row_id,
                        columnId: cell.column_id,
                        value: cell.default_value,
                        updateValue: newValue => updateValue(row.row_id, cell.column_id, newValue),
                        canDelete: canDeleteRow(row.row_id),
                        deleteRow: () => deleteRow(row.row_id),
                    },
                ),
            })),
        }));

        const mappedSubmissionRows = submissionRows.map<Row>(row => ({
            rowId: row.row_id,
            cells: row.cells.map(cell => ({
                columnId: cell.column_id,
                render: () => getComponentForCellType(
                    calculateCellType(cell.column_id, 'USER_ENTRY'),
                    isReadOnly,
                    {
                        rowId: row.row_id,
                        columnId: cell.column_id,
                        value: cell.value,
                        updateValue: newValue => updateValue(row.row_id, cell.column_id, newValue),
                        canDelete: canDeleteRow(row.row_id),
                        deleteRow: () => deleteRow(row.row_id),
                    }
                ),
            })),
        }));

        const rowIds = _.uniq([
            ...mappedDefaultRows.map(row => row.rowId),
            ...mappedSubmissionRows.map(row => row.rowId),
        ]);
        const mappedEmptyCellRows = rowIds.map<Row>(rowId => ({
            rowId,
            cells: columnDefinitions.map(def => ({
                columnId: def.column_id,
                render: () => getComponentForCellType(
                    calculateCellType(def.column_id),
                    isReadOnly,
                    {
                        rowId,
                        columnId: def.column_id,
                        value: '',
                        updateValue: newValue => updateValue(rowId, def.column_id, newValue),
                        canDelete: canDeleteRow(rowId),
                        deleteRow: () => deleteRow(rowId),
                    }
                ),
            }))
        }));

        // Merge the different rows with their cells.
        // Order of merging:
        // 1. All the user-changed/added values have priority, so those cells are filled in first.
        // 2. Cells without values will receive default values.
        // 3. All cells that have still no value, get an empty value as fallback.
        const rowsGroupedByRowId = _.groupBy(
            [...mappedSubmissionRows, ...mappedDefaultRows, ...mappedEmptyCellRows],
            row => row.rowId,
        );
        return Object.keys(rowsGroupedByRowId).map<Row>(rowId => {
            const allCells = _.flatten(rowsGroupedByRowId[rowId].map(row => row.cells));
            const mergedCells = _.uniqBy(allCells, cell => cell.columnId);
            return {
                rowId: parseInt(rowId),
                cells: _.sortBy(mergedCells, cell => columnIds.indexOf(cell.columnId))
                    // Only show cells that have a columnId that is defined in the column definitions.
                    .filter(cell => columnIds.includes(cell.columnId)),
            };
        });
    }, [
        jsonStableStringify(columnDefinitions),
        jsonStableStringify(defaultRows),
        jsonStableStringify(submissionRows),
        minRows,
        canAddRows,
        canRemoveRows
    ]);

    // Only on the first render, if there are not enough rows, we add more until we reach the minimum default amount.
    useEffect(() => {
            const highestRowId = Math.max(0, ...rows.map(row => row.rowId));
            const amountOfRowsToAdd = Math.max(0, minRows - rows.length);
            const rowsToAdd: EnrichtedTableToolSubmissionRow[] = [];
            for (let idOffsetForNewRow = 1; idOffsetForNewRow <= amountOfRowsToAdd; idOffsetForNewRow++) {
                rowsToAdd.push({
                    row_id: highestRowId + idOffsetForNewRow,
                    cells: [],
                    isEphemeral: true,
                });
            }
            setSubmissionRows(prevRows => [...prevRows, ...rowsToAdd]);
        },
        // We omit the dependency array on purpose! We only execute this once!
        []
    );

    const canAddEmptyRow = canAddRows && rows.length < maxRows;
    const addEmptyRow = () => {
        if (!canAddEmptyRow) {
            return;
        }
        const highestRowId = Math.max(0, ...rows.map(row => row.rowId));
        setSubmissionRows(prevRows => [...prevRows, {
            row_id: highestRowId + 1,
            cells: [],
        }]);
    };

    const exposedSubmissionRows = submissionRows
        // If we have any ephemeral rows without content, we filter them out.
        .filter(row => !row.isEphemeral || row.cells.length > 0)
        // We make sure the isEphemeral key does not go outside this hook.
        .map(row => {
            const copiedRow = { ...row };
            delete copiedRow['isEphemeral'];
            // Exclude empty cells from the comparison, as an excluded cell and an empty cell are the same.
            copiedRow.cells = copiedRow.cells.filter(cell => !isEmptyCell(cell));
            return copiedRow;
        });
    const isDirty = initialSubmissionRowsRef.current !== jsonStableStringify(exposedSubmissionRows);

    return {
        headers,
        rows,
        submissionRows: exposedSubmissionRows,
        canAddEmptyRow,
        addEmptyRow,
        maxScore,
        isDirty,
    };
}

export default useTable;
