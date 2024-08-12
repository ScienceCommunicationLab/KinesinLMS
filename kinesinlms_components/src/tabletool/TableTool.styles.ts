import styled from 'styled-components';

type ControlsBarProps = {
    hasNoActions: boolean;
};

export const ControlsBar = styled.div<ControlsBarProps>`
    ${({ hasNoActions }) => hasNoActions && `
        display: none !important;
    `};
`;
