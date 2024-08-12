import {Action, InputType, ActionEvent} from '@projectstorm/react-canvas-core';
import {KeyboardEvent} from 'react';
import {CustomNodeModel, CustomNodeFactory} from "../custom-node";

// Original code from https://github.com/renato-bohler/logossim/blob/dc14949e20cdce636d32653bbbf2ef5bd31f22bc/packages/%40logossim/core/Diagram/actions/ClipboardAction.js
// MIT License: https://github.com/renato-bohler/logossim/blob/master/LICENSE

export interface ClipboardActionOptions {
    keyCodes?: number[];
    modifiers?: {
        ctrlKey?: boolean;
        shiftKey?: boolean;
        altKey?: boolean;
        metaKey?: boolean;
    };
}

/**
 * Handles clipboard actions.
 */
export default class ClipboardAction extends Action {

    // @ts-ignore
    constructor(options: ClipboardActionOptions = {}) {
        const keyCodes: number[] = options.keyCodes || [67, 86, 88];
        const modifiers: any = {
            ctrlKey: false,
            shiftKey: false,
            altKey: false,
            metaKey: false,
            ...options.modifiers
        };
        super({
            type: InputType.KEY_DOWN,
            // @ts-expect-error TS does not realize we have a KeyboardEvent instead of a MouseEvent.
            fire: (event: ActionEvent<KeyboardEvent>) => {
                const {code, ctrlKey, shiftKey, altKey, metaKey} = event.event;
                console.log("event.event: ", event.event);
                // if (this.engine.getModel().isLocked()) return;
                if (ctrlKey && (code === 'KeyX' || code === 'KeyC' || code === 'KeyV')) {
                    console.log("Action we care about fired!");
                    console.log("    event : ", event);
                    console.log("    this : ", this);
                    event.event.preventDefault();
                    if (code === 'KeyX') this.handleCut();
                    if (code === 'KeyC') this.handleCopy();
                    if (code === 'KeyV') this.handlePaste();
                }
            },
        });
    }

    getSelectedComponents = () =>
        this.engine
            .getModel()
            .getSelectedEntities()
            .filter(entity => entity instanceof CustomNodeModel)
            .filter(entity => !entity.isLocked());

    /** Cut */
    handleCut = () => {
        console.log("Handle cut...");
        const selected = this.getSelectedComponents();
        const copies = selected.map(entity => entity.clone().serialize());

        /*
        this.engine.fireEvent(
            {
                nodes: selected,
                links: selected.reduce(
                    (arr, node) => [...arr, ...node.getAllLinks()],
                    [],
                ),
            },
            'entitiesRemoved',
        );
         */
        selected.forEach(node => node.remove());
        this.engine.repaintCanvas();
        localStorage.setItem('clipboard', JSON.stringify(copies));
    };

    /** Copy */
    handleCopy = () => {
        console.log("Handle copy...")
        const copies = this.getSelectedComponents().map(entity =>
            entity.clone().serialize(),
        );
        localStorage.setItem('clipboard', JSON.stringify(copies));
    };


    /** Paste */
    handlePaste = () => {
        console.log("Handle paste...")
        const model = this.engine.getModel();
        const pasteItem = localStorage.getItem('clipboard');
        if (pasteItem === undefined || pasteItem === null) {
            console.log("No item to paste!")
            return;
        }
        const clipboard = JSON.parse(pasteItem);
        if (!clipboard) return;
        model.clearSelection();
        const models = clipboard.map((serialized: any) => {
            const factory = CustomNodeFactory
            const modelInstance = model
                // @ts-expect-error TS does not recognize the specific type of `model`.
                .getActiveNodeLayer()
                .getChildModelFactoryBank(this.engine)
                .getFactory(serialized.type)
                .generateModel({initialConfig: serialized});
            modelInstance.deserialize({
                engine: this.engine,
                data: serialized,
                registerModel: () => {
                },
            });
            return modelInstance;
        });

        models.forEach((modelInstance: any) => {
            let offset = {x: 30, y: 30};
            modelInstance.setPosition(modelInstance.getX() + offset.x, modelInstance.getY() + offset.y);
            // @ts-expect-error TS does not recognize the specific type of `model`.
            model.addNode(modelInstance);
            modelInstance.setSelected(true);
        });

        /*
        localStorage.setItem(
            'clipboard',
            JSON.stringify(
                models.map((modelInstance: any) =>
                    modelInstance.clone().serialize(),
                ),
            ),
        );
         */

        this.engine.repaintCanvas();
    };
}
