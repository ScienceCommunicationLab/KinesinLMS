// @ts-ignore
import React, { useEffect, VFC } from 'react';
import { DeleteCellWrapper } from './DeleteCell.styles';

declare const window: any;

interface Props {
    canDelete: boolean;
    onClick: () => void;
    isReadOnly: boolean;
}

const DeleteCell: VFC<Props> = ({ onClick, canDelete, isReadOnly }) => {
    const isDisabled = isReadOnly || !canDelete;

    const buttonRef = React.useRef<HTMLButtonElement>(null);

    const handleDelete = () => {
        if (isDisabled) return;
        const tooltip = window.bootstrap?.Tooltip.getInstance(buttonRef.current!);
        tooltip?.hide();
        onClick();
    };
    useEffect(() => {
        // Initialize tooltips when first rendering this component, to make sure this component
        // has the Bootstrap tooltips enabled when dynamically added.
        window.klmsEnableTooltips();
    }, []);

    return (
        <DeleteCellWrapper>
            <button
                ref={buttonRef}
                type="button"
                className="btn btn-danger"
                data-bs-toggle="tooltip"
                data-bs-placement="top"
                title="Delete this row"
                disabled={isDisabled}
                onClick={handleDelete}
            >
                <i className="bi bi-trash-fill"></i>
            </button>
        </DeleteCellWrapper>
    );
};

export default DeleteCell;
