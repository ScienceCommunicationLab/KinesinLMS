import {PortModel, PortModelAlignment} from '@projectstorm/react-diagrams';
import {CustomLinkModel} from "../custom-link/custom-link-model";

export class CustomPortModel extends PortModel {
	constructor(alignment: PortModelAlignment) {
		super({
			type: 'custom',
			name: alignment,
			alignment: alignment
		});
	}

	createLinkModel(): CustomLinkModel {
		return new CustomLinkModel({ createdFromPort: this });
	}

	canLinkToPort(port: PortModel): boolean {
		// Prevent linking this port to the same port.
		if (port.getID() === this.getID()) return false;
		return super.canLinkToPort(port);
	}
}
