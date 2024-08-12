import { renderHook } from '@testing-library/react';
import useTable from './useTable';
import { Cell } from "../TableTool.types";
import { JSXElementConstructor } from "react";
import StaticCell from "../components/cells/StaticCell";
import UserEntryCell from "../components/cells/UserEntryCell";

describe('useTable hook', () => {
    describe('rows', () => {
        it('should correctly add empty rows to reach the min rows if the existing rows are not enough', () => {
            const {result} = renderHook(() => useTable({
                columnDefinitions: [
                    {
                        "header": "A",
                        "column_id": "a",
                        "default_cell_type": "USER_ENTRY",
                    },
                    {
                        "header": "B",
                        "column_id": "b",
                        "default_cell_type": "USER_ENTRY"
                    },
                    {
                        "header": "C",
                        "column_id": "c",
                        "default_cell_type": "USER_ENTRY"
                    },
                ],
                canAddRows: true,
                canRemoveRows: true,
                initialSubmissionRows: [
                    {
                        row_id: 1,
                        cells: [
                            {
                                column_id: 'a',
                                value: 'test'
                            }
                        ]
                    },
                    {
                        row_id: 2,
                        cells: [
                            {
                                column_id: 'b',
                                value: 'demo'
                            }
                        ]
                    }
                ],
                defaultRows: [
                    {
                        row_id: 1,
                        cells: [
                            {
                                column_id: 'b',
                                default_value: 'dummy',
                                cell_type: 'STATIC',
                            }
                        ]
                    },
                    {
                        row_id: 3,
                        cells: [
                            {
                                column_id: 'c',
                                default_value: 'fixed',
                                cell_type: 'STATIC',
                            }
                        ]
                    }
                ],
                minRows: 5,
                isReadOnly: false,
                maxRows: 100,
                maxScore: 1
            }));

            // 2 -> the 2 initialSubmissionRows
            expect(result.current.submissionRows.length).toBe(2);
            // 5 -> the 2 initialSubmissionRows, 1 extra from the defaultRows, 2 extra empty ones.
            expect(result.current.rows.length).toBe(5);
        });
    });

    describe('add new row button', () => {
        it('should correctly show the add new row button when table is empty except some default rows', () => {
            const {result} = renderHook(() => useTable({
                columnDefinitions: [
                    {
                        "header": "A",
                        "column_id": "a",
                        "default_cell_type": "USER_ENTRY"
                    },
                    {
                        "header": "B",
                        "column_id": "b",
                        "default_cell_type": "USER_ENTRY"
                    },
                    {
                        "header": "C",
                        "column_id": "c",
                        "default_cell_type": "USER_ENTRY"
                    },
                ],
                canAddRows: true,
                canRemoveRows: true,
                initialSubmissionRows: [],
                minRows: 3,
                defaultRows: [],
                isReadOnly: false,
                maxRows: 100,
                maxScore: 1
            }));

            expect(result.current.canAddEmptyRow).toBe(true);
        });

        it('should correctly hide the add new row button when table is empty, but default empty rows equal the max rows', () => {
            const {result} = renderHook(() => useTable({
                columnDefinitions: [
                    {
                        "header": "A",
                        "column_id": "a",
                        "default_cell_type": "USER_ENTRY"
                    },
                    {
                        "header": "B",
                        "column_id": "b",
                        "default_cell_type": "USER_ENTRY"
                    },
                    {
                        "header": "C",
                        "column_id": "c",
                        "default_cell_type": "USER_ENTRY"
                    },
                ],
                canAddRows: true,
                canRemoveRows: true,
                initialSubmissionRows: [],
                minRows: 5,
                defaultRows: [],
                isReadOnly: false,
                maxRows: 5,
                maxScore: 1
            }));

            expect(result.current.canAddEmptyRow).toBe(false);
        });
    });

    it('should correctly override the cell types on cell level when they differ from the column definition', () => {
        const {result} = renderHook(() => useTable({
            columnDefinitions: [
                {
                    "header": "Goals",
                    "column_id": "goals",
                    "default_cell_type": "STATIC"
                },
                {
                    "header": "Possible Mentors",
                    "column_id": "possible_mentors",
                    "default_cell_type": "USER_ENTRY"
                }
            ],
            defaultRows: [
                {
                    "cells": [
                        {
                            "cell_type": "STATIC",
                            "column_id": "goals",
                            "default_value": "Short-term"
                        },
                        {
                            "cell_type": "STATIC",
                            "column_id": "possible_mentors",
                            "default_value": ""
                        }
                    ],
                    "row_id": 1
                },
                {
                    "cells": [
                        {
                            "cell_type": "USER_ENTRY",
                            "column_id": "goals",
                            "default_value": "1."
                        }
                    ],
                    "row_id": 2
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
                            "column_id": "possible_mentors",
                            "default_value": ""
                        }
                    ],
                    "row_id": 3
                },
                {
                    "cells": [
                        {
                            "cell_type": "USER_ENTRY",
                            "column_id": "goals",
                            "default_value": "1."
                        }
                    ],
                    "row_id": 4
                },
            ],
            canAddRows: false,
            canRemoveRows: false,
            initialSubmissionRows: [],
            minRows: 3,
            maxRows: 100,
            isReadOnly: false,
            maxScore: 1
        }));

        expect(result.current.rows.length).toEqual(4);
        expect(result.current.rows[0].rowId).toEqual(1);
        expect(result.current.rows[0].cells.length).toEqual(2);

        expect(result.current.rows[0].cells[0].columnId).toEqual('goals');
        expect(getCellRenderComponentName(result.current.rows[0].cells[0])).toEqual(StaticCell.name);
        expect(result.current.rows[0].cells[1].columnId).toEqual('possible_mentors');
        expect(getCellRenderComponentName(result.current.rows[0].cells[1])).toEqual(StaticCell.name);

        expect(result.current.rows[1].cells[0].columnId).toEqual('goals');
        expect(getCellRenderComponentName(result.current.rows[1].cells[0])).toEqual(UserEntryCell.name);
        expect(result.current.rows[1].cells[1].columnId).toEqual('possible_mentors');
        expect(getCellRenderComponentName(result.current.rows[1].cells[1])).toEqual(UserEntryCell.name);

        expect(result.current.rows[2].cells[0].columnId).toEqual('goals');
        expect(getCellRenderComponentName(result.current.rows[2].cells[0])).toEqual(StaticCell.name);
        expect(result.current.rows[2].cells[1].columnId).toEqual('possible_mentors');
        expect(getCellRenderComponentName(result.current.rows[2].cells[1])).toEqual(StaticCell.name);

        expect(result.current.rows[3].cells[0].columnId).toEqual('goals');
        expect(getCellRenderComponentName(result.current.rows[3].cells[0])).toEqual(UserEntryCell.name);
        expect(result.current.rows[3].cells[1].columnId).toEqual('possible_mentors');
        expect(getCellRenderComponentName(result.current.rows[3].cells[1])).toEqual(UserEntryCell.name);
    });
});

function getCellRenderComponentName(cell: Cell): string | null {
    return (cell.render()?.type as JSXElementConstructor<any>)?.name ?? null;
}
