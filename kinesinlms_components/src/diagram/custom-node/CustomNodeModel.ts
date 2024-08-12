import {NodeModel, NodeModelGenerics, PortModelAlignment} from '@projectstorm/react-diagrams';
import {CustomPortModel} from '../custom-port';
import {DeserializeEvent} from "@projectstorm/react-canvas-core";
import { CustomNodeTypes } from './CustomNodeTypes';

export interface CustomNodeModelGenerics {
    PORT: CustomPortModel;
}

export class CustomNodeModel extends NodeModel<NodeModelGenerics & CustomNodeModelGenerics> {

    name?: string;
    mindMapType : CustomNodeTypes.PERSON | CustomNodeTypes.CATEGORY | CustomNodeTypes.BASIC;
    mindMapSubtype: string = '';
    mindMapLabel: string = '';

    //font awesome class style for <i> ... e.g. 'fas fa-users-class'
    iconClassName: string = '';

    backgroundColor: string | number | undefined = '#FFFFFF';

    // Indicates if this node already exists when loading the page.
    isAlreadySaved: boolean = false;

    public static createExisting(): CustomNodeModel {
        const model = new CustomNodeModel();
        model.isAlreadySaved = true;
        return model;
    }

    constructor(
        mindMapType: CustomNodeTypes = CustomNodeTypes.PERSON,
        backgroundColor: string = "#ffffff"
    ) {
        super({
            type: 'Custom'
        });
        this.addPort(new CustomPortModel(PortModelAlignment.TOP));
        this.addPort(new CustomPortModel(PortModelAlignment.LEFT));
        this.addPort(new CustomPortModel(PortModelAlignment.BOTTOM));
        this.addPort(new CustomPortModel(PortModelAlignment.RIGHT));
        this.mindMapType = mindMapType;
        this.backgroundColor = backgroundColor;
    }

    serialize() {
        return {
            ...super.serialize(),
            name: this.name,
            mindMapType: this.mindMapType,
            mindMapSubtype: this.mindMapSubtype,
            mindMapLabel: this.mindMapLabel,
            iconClassName: this.iconClassName,
            backgroundColor: this.backgroundColor,
        };
    }

    deserialize(event: DeserializeEvent<this>): void {
        super.deserialize(event);
        this.name = event.data.name;
        this.mindMapType = event.data.mindMapType;
        this.mindMapSubtype = event.data.mindMapSubtype;
        this.mindMapLabel = event.data.mindMapLabel;
        this.iconClassName = event.data.iconClassName;
        this.backgroundColor = event.data.backgroundColor;
    }


}

export function isCustomNodeModel(nodeModel: unknown): nodeModel is CustomNodeModel {
    return (nodeModel as CustomNodeModel)?.getType?.() === 'Custom'
        && !!(nodeModel as CustomNodeModel)?.mindMapType;
}
