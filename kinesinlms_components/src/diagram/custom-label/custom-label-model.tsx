import {LabelModel} from '@projectstorm/react-diagrams';
import {BaseModelGenerics, BaseModelOptions, DeserializeEvent} from '@projectstorm/react-canvas-core';
import {CustomLinkModel} from "../custom-link/custom-link-model";

export interface CustomLabelModelOptions extends BaseModelOptions {
    strength?: number;
}

export interface CustomLabelModelGenerics extends BaseModelGenerics {
    PARENT: CustomLinkModel;
    OPTIONS: CustomLabelModelOptions;
}

export class CustomLabelModel<G extends CustomLabelModelGenerics = CustomLabelModelGenerics> extends LabelModel<G> {

    _strength!: number;

    public get strength(): number {
        return this._strength;
    }

    public set strength(value) {
        if (this.parent) {
            this.parent.getOptions().width = value;
        }
        this._strength = value;
    }


    constructor(options: CustomLabelModelOptions = {}) {
        super({
            ...options,
            type: 'editable-label'
        });
        this.strength = options.strength || 1;
    }

    serialize() {
        return {
            ...super.serialize(),
            strength: this.strength
        };
    }

    deserialize(event: DeserializeEvent<this>): void {
        super.deserialize(event);
        this.strength = event.data.strength;
    }

}
