// @ts-ignore
import React, {ChangeEvent, useEffect, useRef, VFC} from 'react';
import { ReadOnlyContent, TableTextArea } from './UserEntryCell.styles';

interface Props {
    value: string;
    onUpdateValue: (value: string) => void;
    rowId: number;
    columnId: string;
    isReadOnly: boolean;
}

const UserEntryCell: VFC<Props> = ({
    value: initialValue,
    onUpdateValue,
    rowId,
    columnId,
    isReadOnly,
}) => {
    // We need to keep and update the state of the cell normally.
    const [value, setValue] = React.useState(initialValue);

    // Keep track of the value that is published to the parent component.
    const updatedValue = useRef(initialValue);

    // If the initialValue is changed by the user, sync it up with our state.
    React.useEffect(() => {
        setValue(initialValue)
    }, [initialValue]);

    const onChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
        setValue(e.target.value);
    };

    // To prevent spamming changes, we debounce updates outside this component
    // at max once every 200ms, batching all changes that happen fast (like typing).
    useEffect(() => {
        const timeoutId = window.setTimeout(() => {
            // Make sure to only push an update if the value is actually updated.
            if (value !== updatedValue.current) {
                onUpdateValue(value);
                updatedValue.current = value;
            }
        }, 200);
        return () => window.clearTimeout(timeoutId);
    }, [value]);

    if (isReadOnly) {
        return (
            <ReadOnlyContent>{value}</ReadOnlyContent>
        );
    }

    return (
        <TableTextArea
            data-testid={`editable-cell-textarea-${rowId}-${columnId}`}
            key={`text-${rowId}-${columnId}`}
            value={value}
            onChange={onChange}
        />
    );
}

export default UserEntryCell;
