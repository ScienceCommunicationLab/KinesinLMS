import React, { VFC } from 'react';

interface Props {
    onSave: () => void;
    canSave: boolean;
}

const SaveButton: VFC<Props> = ({ onSave, canSave }) => {
    return (
        <button
            data-testid='table-save-button'
            disabled={!canSave}
            onClick={onSave}
            className="btn btn-primary btn-save">
            Save
        </button>
    )
}

export default SaveButton;
