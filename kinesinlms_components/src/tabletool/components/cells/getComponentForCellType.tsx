import React, { ReactElement } from 'react';
import { TableToolCellType } from '../../TableTool.types';
import DeleteCell from './DeleteCell';
import StaticCell from './StaticCell';
import UserEntryCell from './UserEntryCell';

interface ComponentParams {
    value: string;
    rowId: number;
    columnId: string;
    canDelete: boolean;
    deleteRow: () => void;
    updateValue: (newValue: string) => void;
}

function getComponentForCellType(
    cellType: TableToolCellType | undefined,
    isReadOnly: boolean,
    params: ComponentParams
) {
    const fallback = <></>;
    const cellTypeToComponentMap: { [cellType in TableToolCellType]: ReactElement } = {
        'DELETE': <DeleteCell onClick={params.deleteRow} canDelete={params.canDelete} isReadOnly={isReadOnly}/>,
        'STATIC': <StaticCell htmlContent={params.value}/>,
        'USER_ENTRY': <UserEntryCell
            rowId={params.rowId}
            columnId={params.columnId}
            value={params.value}
            onUpdateValue={params.updateValue}
            isReadOnly={isReadOnly}
        />,
    };
    return cellTypeToComponentMap[cellType!] ?? fallback;
}

export default getComponentForCellType;
