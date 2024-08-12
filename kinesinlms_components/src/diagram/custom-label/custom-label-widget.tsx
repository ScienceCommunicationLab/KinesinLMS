// now we can render all what we want in the label
import { CustomLabelModel } from "./custom-label-model";
import * as React from 'react';
import styled from '@emotion/styled';
import { useState, VFC } from 'react';

export interface FlowAliasLabelWidgetProps {
    model: CustomLabelModel;
}

namespace S {
    // NOTE: this CSS rules allows the user to interact with elements in label.
    export const Label = styled.div<{ isReadOnly: boolean }>`
      cursor: ${({ isReadOnly }) => isReadOnly ? 'default' : 'move'};
      pointer-events: ${({ isReadOnly }) => isReadOnly ? 'none' : 'all'};
      user-select: none;
      font-size: 2rem;
      font-family: monospace;
    `;
}

export const CustomLabelWidget: VFC<FlowAliasLabelWidgetProps> = (props) => {
    const [strength, setStrength] = useState(props.model.strength);

    const isReadOnly = props.model.isLocked();

    const onStrengthClick = () => {
        let newStrength = strength + 1;
        if (newStrength > 3) {
            newStrength = 1;
        }
        setStrength(newStrength);
        props.model.strength = newStrength;
        console.log("setting CustomLabelModel strength to : ", newStrength);
    }

    // @ts-expect-error Global window access, should use React context later.
    if (window.disable_link_strength === true) {
        return null;
    }

    return (
        <S.Label
            isReadOnly={isReadOnly}
        >
            <button
                className="btn btn-light rounded-circle"
                onClick={onStrengthClick}
            >
                {strength}
            </button>
        </S.Label>
    );
};
