import { DefaultLinkModel, PortModel } from "@projectstorm/react-diagrams";

interface CustomLinkModelParams {
    strength?: number;
    /** Pass the port from where the link is created (if any). */
    createdFromPort?: PortModel;
}

export class CustomLinkModel extends DefaultLinkModel {

    constructor({ strength = 1, createdFromPort }: CustomLinkModelParams = {}) {
        super({
            type: 'custom', // <-- here we give it a new type
            width: strength, // we specifically want this to also be width 10
        });

        // If the link is created from a port, we want to prevent the UI from glitching the end of the link to position
        // (0,0) of the diagram. Instead, we path the position to point the same port as it is created from (which is
        // the position of the mouse).
        if (createdFromPort) {
            this.getLastPoint().setPosition(createdFromPort.getPosition());
        }
    }

    serialize() {
        return {
            ...super.serialize(),
            // Semantic alias for the 'width' in the saved JSON.
            strength: this.getOptions().width,
        };
    }

}
