import styled from 'styled-components';

type ControlsBarProps = {
    hasnoactions: boolean;
};

export const ControlsBar = styled.div<ControlsBarProps>`
    ${({ hasnoactions }) => hasnoactions && `
        display: none !important;
    `};
`;
