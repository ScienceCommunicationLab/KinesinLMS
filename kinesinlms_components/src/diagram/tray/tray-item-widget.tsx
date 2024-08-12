import * as React from 'react';
import './tray-widget.module.scss'
import { CustomNodeTypes } from "../custom-node/CustomNodeTypes";
import { EMPTY_MIND_MAP_SUBTYPE } from '../custom-node/mindMapSubtypeMap';

export interface TrayItemWidgetProps {
    mindMapType: CustomNodeTypes;
}

export interface TrayItemWidgetState {
    color: string;
    name: string;
}

export class TrayItemWidget extends React.Component<TrayItemWidgetProps, TrayItemWidgetState> {


    constructor(props: TrayItemWidgetProps) {
        super(props);
        this.state = {
            color: "#ffeedd",
            name: props.mindMapType,
        }
    }

    onDragStart = (event: React.DragEvent) => {
        event.dataTransfer.setData('storm-diagram-mindmaptype', JSON.stringify(this.props.mindMapType));
    }

    getMindMapProps = (type: CustomNodeTypes) => {
        if (type === CustomNodeTypes.PERSON) {
            const { icon } = EMPTY_MIND_MAP_SUBTYPE;
            return {
                nodeIcon: <div className="icon-wrapper"><i className={icon}></i></div>,
                subtypeLabel: 'Mentor',
            }
        }
        if (type === CustomNodeTypes.CATEGORY) {
            return {
                nodeIcon: <div/>,
                subtypeLabel: 'Category',
            }
        }
        if (type === CustomNodeTypes.BASIC) {
            return {
                nodeIcon: <div/>,
                subtypeLabel: 'Node',
            }
        }
        return {
            nodeIcon: <div/>,
            subtypeLabel: '',
        };
    }

    render() {
        const { mindMapType } = this.props;
        const { nodeIcon, subtypeLabel } = this.getMindMapProps(mindMapType);

        return (
            <div className={`kn-custom-node tray-item kn-custom-node-${mindMapType.toLowerCase()}`}
                 style={{
                     position: 'relative',
                 }}
                 color={this.state.color}
                 draggable={true}
                 onDragStart={this.onDragStart}>
                {subtypeLabel}
                {nodeIcon}
            </div>
        );
    }
}
