import styled from 'styled-components';

/*
We use standard trick for making textarea expand to full size of cell.
Needs relative position on td above.
*/
export const TableTextArea = styled.textarea`
    width: 100%;
    height: 100%;
    resize: none;
    position: absolute;
    top: 0;
    left: 0;
`;

export const ReadOnlyContent = styled.span`
  white-space: pre-wrap;
`;
