import { DefaultLinkFactory } from "@projectstorm/react-diagrams";
import { CustomLinkModel } from "./custom-link-model";
import * as React from "react";

export class CustomLinkFactory extends DefaultLinkFactory {
    constructor() {
        super('custom'); // <-- this matches with the link model above
    }

    generateModel(): CustomLinkModel {
        const customLinkModel = new CustomLinkModel();
        console.log("generating custom link model!...", customLinkModel);
        return customLinkModel; // <-- this is how we get new instances
    }

    generateLinkSegment(model: CustomLinkModel, selected: boolean, path: string): JSX.Element {
        // @ts-expect-error Global window access, should use React context later.
        if (window.disable_link_strength === true) {
            model.getOptions().width = 1;
        }
        return super.generateLinkSegment(model, model.isLocked() ? false : selected, path);
    }
}
