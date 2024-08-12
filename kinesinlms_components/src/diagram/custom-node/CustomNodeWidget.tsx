import * as React from 'react';
import { RefObject } from 'react';
import { CustomNodeModel } from './CustomNodeModel';
import { CustomNodeTypes } from './CustomNodeTypes';
import { DiagramEngine, PortModel, PortModelAlignment, PortWidget } from '@projectstorm/react-diagrams';
import ContentEditable from 'react-contenteditable'
import mindMapSubtypeMap, { EMPTY_MIND_MAP_SUBTYPE } from './mindMapSubtypeMap';
import MentorSelectionButton from './MentorSelectionButton';

import './custom-node-widget.module.scss';

export interface CustomNodeWidgetProps {
    node: CustomNodeModel;
    engine: DiagramEngine;
}

export interface CustomNodeWidgetState {
    content: string;
}

export class CustomNodeWidget extends React.Component<CustomNodeWidgetProps, CustomNodeWidgetState> {

    contentEditable: RefObject<any>;

    constructor(props: any) {
        super(props)
        this.contentEditable = React.createRef();
        this.state = { content: "" };

        this.setMindMapNodeProps(this.props.node.mindMapSubtype as keyof typeof mindMapSubtypeMap || "");
    };


    onContentEditableKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
        console.log("onContentEditableKeyDown keydown e : ", event.key)
        console.log(event);
        if (event.key === "Backspace" || event.key === "Delete") {
            event.stopPropagation();
        }
    }

    handleChange = (evt: any) => {
        // When there are only spaces, newlines ... clear the value.
        // This will make sure the contenteditable is actually empty and will show the placeholder.
        // We check this with the innerText instead of the value, because whitespaces are `&nbsp;` in the value instead
        // of actual spaces, thus we cannot 'trim' `&nbsp` to check if it is empty/invisible.
        const contentEditableText = evt.currentTarget?.innerText || '';
        if (contentEditableText.trim().length === 0) {
            this.props.node.name = undefined;
        } else {
            this.props.node.name = evt.target.value;
        }
    };

    getPort = (alignment: PortModelAlignment): PortModel => {
        const port = this.props.node.getPort(alignment);
        if (port === undefined || port === null) {
            throw Error(`Undefined port ${alignment}`);
        }
        return port;
    }

    setMindMapNodeProps = (subtype: keyof typeof mindMapSubtypeMap | "" = "") => {
        if (this.props.node.mindMapType === CustomNodeTypes.PERSON) {
            const { label, icon } = mindMapSubtypeMap[subtype as keyof typeof mindMapSubtypeMap] || EMPTY_MIND_MAP_SUBTYPE;

            this.props.node.mindMapSubtype = subtype;
            this.props.node.mindMapLabel = label;
            this.props.node.iconClassName = icon;
        }
    };

    render() {
        const isReadOnly = this.props.engine.getModel().isLocked();

        const {
            mindMapType,
            mindMapSubtype,
            mindMapLabel,
            iconClassName,
            isAlreadySaved,
        } = this.props.node;

        const placeholderText = {
            [CustomNodeTypes.PERSON]: '( name )',
            [CustomNodeTypes.CATEGORY]: '( category )',
            [CustomNodeTypes.BASIC]: '( node )',
        }[mindMapType] ?? '';

        let nodeIcon = <div />;
        if (mindMapType == CustomNodeTypes.PERSON) {
            nodeIcon = (
                <MentorSelectionButton
                    isAlreadySaved={isAlreadySaved}
                    hasSubtype={mindMapSubtype !== ""}
                    label={mindMapLabel}
                    icon={iconClassName}
                    onSelection={this.setMindMapNodeProps}
                    isReadOnly={isReadOnly}
                />
            );
        }

        // Prevent selection and their visual cues when the diagram is read-only.
        // When clicking we trigger a re-render that will instantly deselect the node again,
        // before it can actually render the selected state.
        if (isReadOnly) {
            this.props.node.setSelected(false);
        }

        return (
            <div
                className={`kn-custom-node kn-custom-node-${mindMapType.toLowerCase()} ${isReadOnly ? 'readonly' : ''}`}
                style={{
                    position: 'relative',
                    minWidth: 180,
                    minHeight: 60,
                    borderWidth: this.props.node.isSelected() ? 3 : 1,
                    background: this.props.node.backgroundColor as string
                }}
            >

                <ContentEditable
                    className={`kn-custom-node-text ${isReadOnly ? 'readonly' : ''}`}
                    innerRef={this.contentEditable}
                    html={this.props.node.name || ''} // innerHTML of the editable div
                    placeholder={placeholderText}
                    disabled={isReadOnly}
                    onChange={this.handleChange} // handle innerHTML change
                    tagName='article' // Use a custom HTML tag (uses a div by default)
                    onKeyDown={this.onContentEditableKeyDown}
                />

                <PortWidget
                    style={{
                        left: -8,
                        position: 'absolute'
                    }}
                    port={this.getPort(PortModelAlignment.LEFT)}
                    engine={this.props.engine}>
                    <div className={`custom-node-widget-port d-print-none ${isReadOnly ? 'readonly' : ''}`}/>
                </PortWidget>
                <PortWidget
                    style={{
                        top: -8,
                        position: 'absolute'
                    }}
                    port={this.getPort(PortModelAlignment.TOP)}
                    engine={this.props.engine}>
                    <div className={`custom-node-widget-port d-print-none ${isReadOnly ? 'readonly' : ''}`}/>
                </PortWidget>
                <PortWidget
                    style={{
                        right: -8,
                        position: 'absolute'
                    }}
                    port={this.getPort(PortModelAlignment.RIGHT)}
                    engine={this.props.engine}>
                    <div className={`custom-node-widget-port d-print-none ${isReadOnly ? 'readonly' : ''}`}/>
                </PortWidget>
                <PortWidget
                    style={{
                        bottom: -8,
                        position: 'absolute'
                    }}
                    port={this.getPort(PortModelAlignment.BOTTOM)}
                    engine={this.props.engine}>
                    <div className={`custom-node-widget-port d-print-none ${isReadOnly ? 'readonly' : ''}`}/>
                </PortWidget>

                {nodeIcon}

            </div>
        );
    }

}
