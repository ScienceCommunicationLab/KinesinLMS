import React, { useEffect, useMemo, useState, VFC } from 'react';
import mindMapSubtypeMap, { EMPTY_MIND_MAP_SUBTYPE } from './mindMapSubtypeMap';
import { OverlayTrigger, Popover } from 'react-bootstrap';
import useBootstrapReady from "../../hooks/useBootstrapReady";

type MentorType = keyof typeof mindMapSubtypeMap;

interface MentorSelectionButtonProps {
    isAlreadySaved: boolean;
    hasSubtype: boolean;
    label: string;
    icon: string;
    onSelection: (mentorType: MentorType) => void;
    isReadOnly: boolean;
}

const MentorSelectionButton: VFC<MentorSelectionButtonProps> = ({
    isAlreadySaved,
    hasSubtype,
    label,
    icon,
    onSelection,
    isReadOnly,
}) => {
    const [iconWrapperElement, setIconWrapperElement] = useState<HTMLDivElement|null>(null);

    const bootstrapTooltipReady = useBootstrapReady('Tooltip');

    // @ts-ignore
    const openPopupOnLoad = window.open_mentor_type_popup_after_add;
    const [showOverlay, setShowOverlay] = useState(openPopupOnLoad && !isAlreadySaved);

    const tooltip = useMemo(() => {
        if (!iconWrapperElement) return null;
        if (!bootstrapTooltipReady) return null;
        return new window.bootstrap.Tooltip(iconWrapperElement, {
            placement: 'top',
            html: true,
            title: hasSubtype && !isReadOnly ? label + '<br>(click to change)' : label,
            trigger: 'hover focus',
        });
    }, [iconWrapperElement, label, bootstrapTooltipReady, isReadOnly]);

    useEffect(() => {
        if (!bootstrapTooltipReady) return;
        if (isReadOnly && label === EMPTY_MIND_MAP_SUBTYPE.label) {
            tooltip?.disable();
        } else {
            tooltip?.enable();
        }
    }, [bootstrapTooltipReady]);

    useEffect(() => {
        // The first time the tooltip element is ready, show the tooltip by default.
        // This will happen after adding the mentor node to the diagram.
        if (!hasSubtype && !openPopupOnLoad && !isAlreadySaved) {
            tooltip?.show();
        }
        return () => tooltip?.hide();
    }, [tooltip, hasSubtype, isAlreadySaved]);

    useEffect(() => {
        // Make sure the tooltip sticks to the node, so update the tooltip on ever re-render.
        // Should not impact performance, since the popper library will debounce the update calls.
        if (isReadOnly && label === EMPTY_MIND_MAP_SUBTYPE.label) return;
        tooltip?.update();
    });

    useEffect(() => {
        if (isReadOnly && label === EMPTY_MIND_MAP_SUBTYPE.label) return;
        // When the overlay with mentor type selection is shown, we do not want to show the tooltip saying you can
        // change the mentor type by clicking on the button...
        if (showOverlay) {
            tooltip?.hide();
            tooltip?.disable();
        } else {
            tooltip?.enable();
        }
    }, [showOverlay, tooltip]);

    const handleMentorTypeClicked = (mentorType: MentorType) => {
        if (isReadOnly) {
            return;
        }
        setShowOverlay(false);
        onSelection(mentorType);
    };

    const overlay = (
        <Popover>
            <Popover.Body>
                <div className="list-group-flush">
                    {Object.entries(mindMapSubtypeMap).map(([mentorType, { icon, label }]) => (
                        <button
                            key={mentorType}
                            type="button"
                            className="list-group-item list-group-item-action"
                            onClick={() => handleMentorTypeClicked(mentorType as MentorType)}
                        >
                            <i className={`${icon} mentor-selection-icon`} />
                            {label}
                        </button>
                    ))}
                </div>
            </Popover.Body>
        </Popover>
    );

    const SelectionButton = (
        <div ref={setIconWrapperElement} className={`icon-wrapper ${isReadOnly ? 'readonly' : '' }`}>
            <i className={icon}/>
        </div>
    );

    if (isReadOnly) {
        return SelectionButton;
    }
    return (
        <OverlayTrigger
            rootClose
            show={showOverlay}
            onToggle={setShowOverlay}
            trigger='click'
            placement='right'
            overlay={overlay}
        >
            {SelectionButton}
        </OverlayTrigger>
    );
};

export default MentorSelectionButton;
