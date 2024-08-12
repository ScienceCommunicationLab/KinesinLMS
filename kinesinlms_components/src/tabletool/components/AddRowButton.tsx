// @ts-ignore
import React, { VFC } from 'react';
import { AddRowButtonWrapper } from './AddRowButton.styles';

interface Props {
    onAdd: () => void;
    canAdd: boolean;
}

declare const window: any;

const AddRowButton: VFC<Props> = ({ onAdd, canAdd }) => {
    const isDisabled = !canAdd;

    const buttonRef = React.useRef<HTMLButtonElement>(null);

    const handleClick = () => {
        if (isDisabled) return;
        if (buttonRef.current) {
            const tooltip = window.bootstrap?.Tooltip.getInstance(buttonRef.current);
            tooltip?.hide();
        }
        onAdd();
    }

    return (
        <AddRowButtonWrapper>
            <button
                ref={buttonRef}
                className="btn btn-secondary"
                data-bs-toggle="tooltip"
                data-bs-placement="top"
                title="Add row to table"
                disabled={isDisabled}
                onClick={handleClick}
            >
                <i className="bi bi-plus-circle"></i>
                &nbsp;Row
            </button>
        </AddRowButtonWrapper>
    )
};

export default AddRowButton;
