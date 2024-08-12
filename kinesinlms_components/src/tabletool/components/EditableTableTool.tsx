import React, { VFC } from 'react';
import { Table, TableCell, TableHeader, TableRow } from './EditableTableTool.styles';
import { Header, Row } from '../TableTool.types';
import { DELETE_ROW_COLUMN_ID } from '../hooks/useTable';

interface Props {
    headers: Header[];
    rows: Row[];
}

const EditableTableTool: VFC<Props> = ({
    headers,
    rows,
}) => {
    const amountOfColumns = headers.filter(header => header.columnId !== DELETE_ROW_COLUMN_ID).length;

    return (
        <Table>
            <thead>
                <TableRow>
                    {headers.map(header => (
                        <TableHeader
                            amountOfColumns={amountOfColumns}
                            key={header.columnId}
                        >
                            {header.value}
                        </TableHeader>
                    ))}
                </TableRow>
            </thead>
            <tbody>
                {rows.map(row => (
                    <TableRow key={row.rowId}>
                        {row.cells.map(cell => (
                            <TableCell key={`${row.rowId}_${cell.columnId}`}>
                                {cell.render()}
                            </TableCell>
                        ))}
                    </TableRow>
                ))}
            </tbody>
        </Table>
    );
}

export default EditableTableTool;
