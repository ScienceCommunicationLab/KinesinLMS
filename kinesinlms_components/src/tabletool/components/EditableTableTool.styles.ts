import styled, { css } from 'styled-components';

/*
STYLES:
Only add styles specific to the TableTool here.
More generic styles applicable to all SITs should
go in sit.scss in the Django app.
*/

export const Table = styled.table`
    border-spacing: 0;
    border: 1px solid black;
`;

const TableCellCss = css`
    margin: 0;
    padding: 0.5rem;
    border-bottom: 1px solid black;
    border-right: 1px solid black;
    position: relative;
    vertical-align: top;
    &:last-child {
        border-right: 0;
    }
`;

interface TableHeaderProps {
    amountofcolumns: number;
}

export const TableHeader = styled.th<TableHeaderProps>`
  ${TableCellCss};
  width: ${({ amountofcolumns }) => 100 / amountofcolumns}%;
`;

export const TableCell = styled.td`
    ${TableCellCss};
`;

export const TableRow = styled.tr`
    tbody > & {
        height: 100px;
    }

    &:last-child {
        ${TableCell} {
            border-bottom: 0;
        }
    }
`;
