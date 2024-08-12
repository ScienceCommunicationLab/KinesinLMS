import {CustomNodeWidget} from './CustomNodeWidget';
import {CustomNodeModel} from './CustomNodeModel';
import * as React from 'react';
import {AbstractReactFactory, GenerateWidgetEvent, GenerateModelEvent} from '@projectstorm/react-canvas-core';
import {DiagramEngine} from '@projectstorm/react-diagrams';

export class CustomNodeFactory extends AbstractReactFactory<CustomNodeModel, DiagramEngine> {
    constructor() {
        super('Custom');
    }

    generateReactWidget(event: GenerateWidgetEvent<any>): JSX.Element {
        return <CustomNodeWidget engine={this.engine} node={event.model} />;
    }

    generateModel(event: GenerateModelEvent) {
        return CustomNodeModel.createExisting();
    }
}
