import * as React from 'react';
import { AbstractReactFactory, GenerateWidgetEvent } from '@projectstorm/react-canvas-core';
import { DiagramEngine } from '@projectstorm/react-diagrams';
import {CustomLabelModel} from "./custom-label-model";
import {CustomLabelWidget} from "./custom-label-widget";


export class CustomLabelFactory extends AbstractReactFactory<CustomLabelModel, DiagramEngine> {
	constructor() {
		super('editable-label');
	}

	generateModel(): CustomLabelModel {
		return new CustomLabelModel();
	}

	generateReactWidget(event: GenerateWidgetEvent<CustomLabelModel>): JSX.Element {
		return <CustomLabelWidget model={event.model} />;
	}
}
