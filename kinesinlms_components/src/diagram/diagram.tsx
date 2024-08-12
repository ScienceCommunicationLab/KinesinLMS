import createEngine, { DiagramModel, LabelModel, NodeModel, PortModelAlignment, DiagramEngine } from '@projectstorm/react-diagrams';
import * as React from 'react';
import { createRef, useEffect, useState, VFC } from 'react';
import * as _ from 'lodash';
import axios, { AxiosRequestConfig, Method } from 'axios';
import { BaseModel, CanvasWidget, SelectionBoxLayerFactory } from '@projectstorm/react-canvas-core';

import { CustomNodeFactory, CustomNodeModel } from './custom-node';
import { CustomPortFactory, CustomPortModel } from './custom-port';
import { TrayItemWidget } from "./tray/tray-item-widget";
import { DiagramCanvasWidget } from './canvas/diagram-canvas-widget';
import ClipboardAction from "./actions/clipboard-action";
import { default as TwitterPicker } from '../colorpicker/Twitter';
import { OverlayTrigger, Toast, Tooltip } from 'react-bootstrap';

import './diagram.module.scss';
import { CustomLinkFactory } from "./custom-link/custom-link-factory";
import { CustomLabelFactory } from "./custom-label/custom-label-factory";
import { CustomLabelModel } from './custom-label/custom-label-model';
import { isCustomNodeModel } from "./custom-node/CustomNodeModel";
import { CustomNodeTypes } from "./custom-node/CustomNodeTypes";
import mindMapSubtypeMap from './custom-node/mindMapSubtypeMap';
import { CustomLinkModel } from './custom-link/custom-link-model';
import DiagramChangeDetector from './utils/DiagramChangeDetector';
import { defaultTrayNodesType, getNodesForTrayNodesType } from './tray/trayNodesTypes';
import {DiagramToolDefinition, isDiagramToolMentorCategoryDefinitionProps} from './diagram.types';
import SITScores from '../SITScores';
import deleteKeysFromObject from '../utils/deleteKeysFromObject';
// @ts-ignore
import jsonStableStringify from "json-stable-stringify";

/*

Diagram Component
--------------------------------------

This component renders a "DiagramTool" for use by a student in a course.
(A separate component is used for instructors who want to author templates.)

It expects certain props to be set by Django / react-templatetags, and
will try to save results back to Django via the simple_interactive_tool API.

Note: What's up with using camelCase *and* snake_case?

    Since this React component is embedded in a Django app, we tend to send incoming
    props as variables in snake_case. We keep that convention in this class for
    these 'incoming' variables to remember their Django origins.

    For variables that are local to this React application, however, we use
    SnakeCase since that seems most conventional in React apps.

    Maybe I'll dump this approach in the future if it isn't helpful.

*/

export type DiagramModeTypes = 'BASIC' | 'TEMPLATE';


export interface DiagramProps {
    // Props incoming from Django via django-react-templatetags.
    // Notice the snake case.

    // mode can be BASIC or TEMPLATE
    // BASIC is for when student is building a diagram submission.
    // TEMPLATE is for when admins are building diagram templates.
    mode: DiagramModeTypes;

    status: string;
    score: number;
    max_score: number;
    has_template: boolean;
    read_only: boolean;

    // BASIC mode props...
    course_id: number;
    course_unit_id: number;
    course_unit_slug: string;
    simple_interactive_tool_id: number;
    definition: DiagramToolDefinition;
    existing_simple_interactive_tool_submission_id: number | null;
    // existing_simple_interactive_tool_submission holds the student's diagram if one exists
    existing_simple_interactive_tool_submission: any;
    // tray_instructions: string | null;
    // disable_link_strength: boolean;

    //TEMPLATE mode props....
    simple_interactive_template_id: number | null;
    template_json: any;

}

export interface DiagramState {
    // State for this app... a mix of values copied from incoming
    // props and custom internal state we need for component functioning.
    // Vars that come from the Django app are in snake case.

    existing_simple_interactive_tool_submission_id: number | null;
    savedModel: string;
    status: string;
    score: number;
    maxScore: number;
    sendInProgress: boolean;
    submissionSuccess: boolean;
    submissionError: string;
    // Keep track of changes after loading a diagram,
    // so we can activate the "Save" button.
    hasChanges: boolean;
    // Same as `hasChanges`, but we will also trigger a
    // dialog to notify the user has unsaved changes
    // when unloading the window.
    hasBlockingChanges: boolean;
    // If this error is populated, it will contain the reason why
    // the user cannot save the diagram. It can be used to disable
    // the "Save" button.
    cannotSaveError: string | null;
    hasTemplate: boolean;
    displayLineColorPicker: boolean;
    displayFillColorPicker: boolean;
    currentLineColor: string;
    currentFillColor: string;
    showSaveToast: boolean;
    // Flag to indicate whether to show diagram in read-only
    // view or not.
    readOnly: boolean;
}

export default class Diagram extends React.Component<DiagramProps, DiagramState> {

    engine!: DiagramEngine;
    model!: DiagramModel;
    diagramChangeDetector!: DiagramChangeDetector;

    private repaintCanvasListenerDeregister: Function | null = null;
    private repaintCanvasHandlerDebounceTimeoutId: any;

    private wrapperRef = createRef<HTMLDivElement>();

    /**
     * Helper function to easily get/query HTML/SVG elements that are children of this component.
     */
    private querySelectorAll = (selector: string) => {
        const nodeList = this.wrapperRef.current?.querySelectorAll(selector) ?? new NodeList();
        const elements: (HTMLElement | SVGElement)[] = [];
        nodeList.forEach(node => {
            if (node instanceof HTMLElement || node instanceof SVGElement) {
                elements.push(node);
            }
        });
        return elements;
    };

    handleBeforePrint = () => {
        const reactCanvas = this.querySelectorAll('.react-canvas')?.[0];
        const reactCanvasChildren = this.querySelectorAll('.react-canvas > *');
        if (!reactCanvas || reactCanvasChildren.length < 0) {
            return;
        }

        const visibleWidth = 630; // Width used on a regular A4 page...
        const widestChildWidth = Math.max(...reactCanvasChildren.map(child => child.scrollWidth));
        const ratio = Math.max(visibleWidth / widestChildWidth, 0.1).toFixed(4);
        reactCanvas.style.setProperty('--scale-ratio', ratio);
    };

    validateIncomingProps() {
        if (this.props.mode == "BASIC") {
            if (!this.props.simple_interactive_tool_id) {
                throw Error("Cannot load diagram. The diagram ID is not present. Please reload this page and try again.");
            }
            if (!this.props.course_id) {
                throw Error("Cannot load diagram. The course ID is not present. Please reload this page and try again.");
            }
        }
    }

    constructor(props: DiagramProps) {
        console.log("Diagram constructor. Props: ", props);
        super(props);
        this.validateIncomingProps();
        this.repaintCanvasHandlerDebounceTimeoutId = -1;

        window.addEventListener('beforeprint', this.handleBeforePrint);

        // TODO: these settings could be added to React context, but first we need to make Diagram components use hooks!
        // @ts-expect-error Assigning property on window
        window.open_mentor_type_popup_after_add = this.props.definition.open_mentor_type_popup_after_add || false;
        // @ts-expect-error Assigning property on window
        window.disable_link_strength = this.props.definition.disable_link_strength || false;
        // @ts-expect-error Assigning property on window
        window.tray_nodes_type = this.props.definition.tray_nodes_type || defaultTrayNodesType;
        // @ts-expect-error Assigning property on window
        window.can_save_without_mentor_type = isDiagramToolMentorCategoryDefinitionProps(this.props.definition)
            ? this.props.definition.can_save_without_mentor_type || false
            : false;

        let saved_diagram: any;
        if (props.mode == "TEMPLATE") {
            saved_diagram = props.template_json;
        } else {
            saved_diagram = props.existing_simple_interactive_tool_submission;
        }

        this.state = {
            // we move the submission ID from props to state b/c it might be 0 or null at first, but
            // then we'll get a new ID from the server response on first save.
            existing_simple_interactive_tool_submission_id: props.existing_simple_interactive_tool_submission_id,
            savedModel: saved_diagram,
            status: props.status,
            score: props.score,
            maxScore: props.max_score,
            sendInProgress: false,
            submissionSuccess: false,
            submissionError: '',
            hasChanges: false,
            hasBlockingChanges: false,
            cannotSaveError: null,
            hasTemplate: props.has_template || false,
            displayFillColorPicker: false,
            displayLineColorPicker: false,
            currentLineColor: "#000000",
            currentFillColor: "#555555",
            showSaveToast: false,
            readOnly: props.read_only || false,
        }
        console.log("State: ", this.state);

        //set up the diagram engine
        this.engine = createEngine({
            registerDefaultZoomCanvasAction: false,
        });

        // Turn off points...makes the diagram easier to use and
        // our students don't need complex connectors
        this.engine.maxNumberPointsPerLink = 0;

        //add actions
        this.engine
            .getActionEventBus()
            .registerAction(new ClipboardAction());

        // Register factories
        this.engine.getPortFactories().registerFactory(
            new CustomPortFactory('custom', (config) =>
                new CustomPortModel(PortModelAlignment.LEFT)
            )
        );
        this.engine.getNodeFactories().registerFactory(new CustomNodeFactory());
        this.engine.getLinkFactories().registerFactory(new CustomLinkFactory());
        this.engine.getLayerFactories().registerFactory(new SelectionBoxLayerFactory());
        this.engine.getLabelFactories().registerFactory(new CustomLabelFactory());

        //setup the diagram model
        let diagramJSON = null;
        if (this.state.savedModel) {
            diagramJSON = this.state.savedModel
        }
        this.model = this.createDiagramModel(diagramJSON, this.engine);

        if (this.state.readOnly) {
            this.model.setLocked(true);
        }

        //load model into engine
        this.engine.setModel(this.model);

        /* Set up constants and defaults for Axios */
        axios.defaults.xsrfCookieName = 'csrftoken';
        axios.defaults.xsrfHeaderName = 'X-CSRFToken';

        // Make sure 'this' point to this component for functions used in callbacks.
        this.handleCanvasRepaint = this.handleCanvasRepaint.bind(this);
    }

    createDiagramModel(diagramJSON: any, engine: DiagramEngine): DiagramModel {
        const model = new DiagramModel();
        if (diagramJSON) {
            model.deserializeModel(diagramJSON, engine);
        }
        model.registerListener({
            linksUpdated: (e: any) => {
                console.log("linksUpdated ", e);
                if (e.isCreated) {
                    const createdModelId = e.link.getID();
                    // Only add the label if it does not already exist. Duplicated/copied items are 'created', but
                    // already contain the label from the copy itself.
                    if (!e.link.getLabels().some((label: LabelModel) => label instanceof CustomLabelModel)) {
                        e.link.addLabel(new CustomLabelModel({strength: 1}));
                        // When a new link is created, it is automatically 'selected'. We should deselect all the other
                        // links, to prevent users to accidentally delete multiple links (because previous ones are still
                        // selected).
                        this.model.getModels().forEach(model => {
                            if (model instanceof CustomLinkModel && model.getID() !== createdModelId) {
                                model.setSelected(false);
                            }
                        });
                    }
                }
            }
        });
        return model;
    }

    handleWindowBeforeUnload = (event: BeforeUnloadEvent) => {
        // Since we are using a debounced function to check for changes,
        // we need to check for changes before the user leaves the page
        // to be 100% sure there are any. It is fairly unlikely the user
        // will be in this state, but the check itself is not extremely
        // expensive, so it is justified.
        this.checkDiagramChanges();
        if (this.state.hasBlockingChanges) {
            event.returnValue = true;
            return true;
        }
    }

    componentDidMount() {
        window.addEventListener("beforeunload", this.handleWindowBeforeUnload);
        // Listen for repaint events and handle it.
        const repaintCanvasListener = this.engine.registerListener({
            repaintCanvas: this.handleCanvasRepaint,
        });
        this.repaintCanvasListenerDeregister = repaintCanvasListener.deregister;

        const {deregister} = this.engine.registerListener({
            rendered: () => {
                // Once the engine exists, on the first render this function will be executed,
                // but only once (because of the `deregister` call). We only want to save the
                // initial version of the diagram after it renders, because some parts (e.g.,
                // links) are only calculated after it's being rendered. If we would not wait
                // for this render event, the diagram would immediately being marked as
                // 'changed', even though nothing is different from the saved diagram.
                // We wrap the save of the current diagram in a `setTimeout` without ms param
                // to just postpone the save one `tick`. This makes sure the first render is
                // actually done, as well as the calculations.
                window.setTimeout(() => this.markModelAsSaved());
                deregister();
            },
        });
    }

    componentWillUnmount() {
        window.removeEventListener('beforeprint', this.handleBeforePrint);
        window.removeEventListener("beforeunload", this.handleWindowBeforeUnload);
        if (this.repaintCanvasListenerDeregister) {
            this.repaintCanvasListenerDeregister();
        }
    }

    private checkDiagramChanges() {
        const { hasSoftChanges, hasHardChanges } = this.diagramChangeDetector.hasChanges();
        this.setState({
            hasChanges: hasSoftChanges,
            hasBlockingChanges: hasHardChanges,
        });
    }

    /**
     * This function will be executed every time the diagram is repainted.
     * It compares the saved diagram model with the current model after repainting.
     *
     * Note: this function is debounced (for performance reasons, e.g., while dragging nodes),
     * so will only execute if the repaint is not called for 200ms!
     */
    private handleCanvasRepaint() {
        clearTimeout(this.repaintCanvasHandlerDebounceTimeoutId);
        this.repaintCanvasHandlerDebounceTimeoutId = setTimeout(() => {
            // The model will be null if the diagram is not yet initialized and rendered.
            if (this.state.savedModel === null) {
                return;
            }
            this.validateNodes(this.model.getNodes());
            this.checkDiagramChanges();
        }, 200);
    }

    private validateNodes(nodes: NodeModel[]) {
        for (const node of nodes) {
            // We only want to validate our custom nodes.
            if (!isCustomNodeModel(node)) continue;
            if (node.mindMapType === CustomNodeTypes.PERSON
                && !Object.keys(mindMapSubtypeMap).includes(node.mindMapSubtype)
                // @ts-ignore
                && !window.can_save_without_mentor_type
            ) {
                this.setState({cannotSaveError: "Please select a mentor type for all mentor nodes before saving."});
                return;
            }
        }
        // If we get to this point there are no errors, all good!
        this.setState({cannotSaveError: null});
    }

    /**
     * This marks the current state of the model as 'saved'.
     * The 'saved' model is used to compare the current model to see if there are any changes.
     */
    private markModelAsSaved() {
        const savedModel: string = this.getSerializedModel();
        this.setState({savedModel: savedModel});
        // Since we have a new 'initial' or 'saved' state, we create a new dirty checker.
        this.diagramChangeDetector = new DiagramChangeDetector(this.engine.getModel());
        this.checkDiagramChanges();
    }

    private getSerializedModel(): string {
        const ignoredProps = ['selected'];
        const serializedModel = this.engine.getModel().serialize();
        const cleanedModel = deleteKeysFromObject(serializedModel, ignoredProps);
        return jsonStableStringify(cleanedModel);
    }

    onSaveElements = (event: React.MouseEvent) => {
        if (this.state.cannotSaveError) {
            console.log('cannot save the diagram, because there is a validation error:', this.state.cannotSaveError);
            return;
        }

        const diagram_model_json = JSON.parse(this.getSerializedModel());
        console.log("Saving diagram. Diagram structure: ", diagram_model_json)

        const simpleInteractiveToolSubmissionJSON = {
            simple_interactive_tool: this.props.simple_interactive_tool_id,
            course_unit: this.props.course_unit_id,
            course: this.props.course_id,
            json_content: diagram_model_json
        }
        let requestMethod: Method;
        let targetURL;
        if (this.props.mode == "TEMPLATE") {
            requestMethod = "put"; // always a put...the template is created before showing this diagram tool.
            targetURL = `/api/simple_interactive_tool_templates/${this.props.simple_interactive_template_id}/`;
        } else {
            if (this.state.existing_simple_interactive_tool_submission_id) {
                requestMethod = "put";
                targetURL = "/api/simple_interactive_tool_submissions/" + this.state.existing_simple_interactive_tool_submission_id + "/";
            } else {
                requestMethod = "post";
                targetURL = "/api/simple_interactive_tool_submissions/";
            }
        }

        const config: AxiosRequestConfig = {
            url: targetURL,
            data: simpleInteractiveToolSubmissionJSON,
            withCredentials: true,
            method: requestMethod
        }

        this.setState({sendInProgress: true, submissionSuccess: false})
        console.log("Sending to server:", simpleInteractiveToolSubmissionJSON);
        axios.request(config)
            .then((response: any) => {
                console.log("Diagram: received response from server: ", response);
                this.setState({
                    submissionSuccess: true,
                    sendInProgress: false,
                    existing_simple_interactive_tool_submission_id: response.data.id,
                    status: response.data.status,
                    score: response.data.score,
                    maxScore: response.data.max_score,
                })
                this.setState({showSaveToast: true})
                this.markModelAsSaved();
            })
            .catch((error) => {
                console.error("Error from server:", error);
                if (error.response && error.response.data) {
                    const responseData = error.response.data;
                    let errorMessage = '';
                    if (responseData.detail) {
                        errorMessage = responseData.detail;
                    }
                    if (responseData.non_field_errors) {
                        errorMessage = errorMessage + ". " + responseData.non_field_errors.join(', ');
                    }
                    window.alert(`Could not save diagram data. ${errorMessage}`);
                } else {
                    window.alert(`Could not save diagram data.`);
                }
                this.setState({
                    submissionSuccess: false,
                    submissionError: error,
                    sendInProgress: false
                });
            });
    }

    onDropWidget = (event: React.DragEvent<HTMLDivElement>) => {
        console.log("Item dropped...");
        const mindMapTypeData = event.dataTransfer.getData('storm-diagram-mindmaptype');
        if (!mindMapTypeData) {
            // If some other element is dragged into the diagram, we should just ignore it.
            return;
        }
        const mindMapType = JSON.parse(mindMapTypeData);

        let node: CustomNodeModel;
        if (mindMapType === CustomNodeTypes.PERSON) {
            node = new CustomNodeModel(CustomNodeTypes.PERSON);
        } else if (mindMapType == CustomNodeTypes.CATEGORY) {
            node = new CustomNodeModel(CustomNodeTypes.CATEGORY);
        } else if (mindMapType == CustomNodeTypes.BASIC) {
            node = new CustomNodeModel(CustomNodeTypes.BASIC);
        } else {
            console.error("Unrecognized mindMapType: ", mindMapType);
            return;
        }
        const point = this.engine.getRelativeMousePoint(event);
        node.setPosition(point);
        this.engine.getModel().addNode(node);
        this.forceUpdate();
        this.handleCanvasRepaint();

        // Call function defined in top-level javascript to reset bootstrap tooltips....
        // Wrapped in setTimeout without delay, so it will be called in the next 'tick' in the event loop.
        // This is necessary because the node is not yet rendered immediately, but will be in the next 'tick'.
        setTimeout(() => {
            // @ts-ignore
            window.klmsEnableTooltips();
        });

    }

    onDuplicateSelected = () => {
        const offset = {x: 100, y: 100};
        const model = this.engine.getModel();

        const selectedEntities = model.getSelectedEntities();

        // Contains a reference to all the original diagram items.
        const originalItemsMap: { [id: string]: BaseModel } = {};
        const copiedItemsMap: { [id: string]: CustomNodeModel } = {};
        const originalItemIdToCopiedItemIdMap: { [id: string]: string } = {};

        // Add all nodes to the model.
        _.forEach(selectedEntities, (item: BaseModel) => {
            if (!(item instanceof CustomNodeModel)) return;

            const newItem = item.clone(originalItemsMap) as CustomNodeModel;
            copiedItemsMap[newItem.getID()] = newItem;
            originalItemIdToCopiedItemIdMap[item.getID()] = newItem.getID();

            // Offset the nodes slightly.
            newItem.setPosition(newItem.getX() + offset.x, newItem.getY() + offset.y);
            // Add the node to the model.
            model.addNode(newItem);
            // New items are selected by default, prevent this.
            newItem.setSelected(false);
        });

        // After adding all the nodes to the model, try to duplicate all links. We will only duplicate the links that
        // Have both the 'source' and 'target' node copied as well. So, if one of those are missing in the duplication,
        // we will not copy over the link.
        _.forEach(selectedEntities, (item: BaseModel) => {
            if (!(item instanceof CustomLinkModel)) return;

            // Check if both source and target nodes were also copied over... if so -> continue with the link copy.
            const originalSourceNode = item.getSourcePort().getNode();
            const originalTargetNode = item.getTargetPort().getNode();
            if (
                !(originalSourceNode instanceof CustomNodeModel)
                || !(originalTargetNode instanceof CustomNodeModel)
            ) return;
            const copiedSourceNodeId = originalItemIdToCopiedItemIdMap[originalSourceNode.getID()];
            const copiedTargetNodeId = originalItemIdToCopiedItemIdMap[originalTargetNode.getID()];
            if (!copiedSourceNodeId || !copiedTargetNodeId) return;

            // Copy the link node and connect both the source and target ports (this results in auto-positioning on the
            // diagram).
            const newItem = item.clone() as CustomLinkModel;
            newItem.setSourcePort(copiedItemsMap[copiedSourceNodeId].getPort(item.getSourcePort().getName()));
            newItem.setTargetPort(copiedItemsMap[copiedTargetNodeId].getPort(item.getTargetPort().getName()));
            // Add the node to the model.
            model.addLink(newItem);
            // New items are selected by default, prevent this.
            newItem.setSelected(false);
        });

        this.forceUpdate();
    }

    onDragOver = (event: React.DragEvent<HTMLDivElement>) => {
        event.preventDefault();
    }

    onZoomToFit = (event: React.MouseEvent) => {
        this.engine.zoomToFit();
        this.forceUpdate();
    }

    onKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
        console.log("keydown...");
        if (event.key === "c" && event.ctrlKey) {
            console.log("Ready to copy");
        }
    };

    resetToTemplate = () => {
        const getTemplateJsonURL = `/api/simple_interactive_tool_submissions/${this.state.existing_simple_interactive_tool_submission_id}/template/`;
        const config: AxiosRequestConfig = {
            url: getTemplateJsonURL,
            withCredentials: true,
            method: "get"
        }
        axios.request(config)
            .then((response: any) => {
                console.log("resetToTemplate: response returned from server ", response);
                const templateJSON = response.data;
                if (templateJSON) {
                    console.log("Resetting model to template:", templateJSON);
                    this.model = this.createDiagramModel(templateJSON, this.engine);
                    this.engine.setModel(this.model);
                    this.checkDiagramChanges();
                    this.forceUpdate();
                } else {
                    window.alert("No template available.");
                }
            })
            .catch((error) => {
                console.error("Error from server:", error);
                window.alert("Could not load template from server. Please contact support for help.");
            });
    }

    handleLinePickerClick = () => {
        const selectedCustomNodes = this.getSelectedCustomNodes();
        if (!selectedCustomNodes || selectedCustomNodes.length == 0) {
            window.alert("Please select one or more shapes before using the 'Fill Color' button.")
        } else {
            this.setState({displayLineColorPicker: !this.state.displayLineColorPicker});
        }
    };


    getSelectedCustomNodes = () => {
        const selectedEntities = this.engine.getModel().getSelectedEntities();
        const selectedCustomNodes = selectedEntities.filter(
            (item: BaseModel<any>) => item instanceof CustomNodeModel
        );
        return selectedCustomNodes;
    }


    handleLinePickerClose = () => {
        this.setState({displayLineColorPicker: false})
    };
    handleFillPickerClick = () => {
        this.setState({displayLineColorPicker: !this.state.displayLineColorPicker})
    };

    handleColorChange = (color: any) => {
        const selectedEntities = this.engine.getModel().getSelectedEntities();
        let numChanged = 0;
        selectedEntities.forEach((item: BaseModel<any>) => {
            if (item instanceof CustomNodeModel) {
                numChanged++;
                (item as CustomNodeModel).backgroundColor = color.hex;
                console.log("CustomNodeModel color changed to : ", color);
            }
        });
        if (numChanged == 0) {
            window.alert("Please select one or more shapes before using the 'Fill Color' button.")
        }

        this.engine.repaintCanvas(true);
        this.setState({displayLineColorPicker: false})
        this.forceUpdate();
    }

    handleColorChangeComplete = (event: any) => {
        console.log("setting color to", event)
        this.setState({displayLineColorPicker: false})
        this.forceUpdate();
    }

    handleFillPickerClose = () => {
        this.setState({displayLineColorPicker: false})
        this.forceUpdate();
    };

    handleScroll = (event: any) => {
        event.preventDefault();
        event.stopPropagation();
    }

    handleZoomOut = () => {
        const currZoom = this.model.getZoomLevel();
        this.model.setZoomLevel(currZoom + 10);
        this.forceUpdate();
    }
    handleZoomIn = () => {
        const currZoom = this.model.getZoomLevel();
        this.model.setZoomLevel(currZoom - 10);
        this.forceUpdate();
    }

    render() {

        let savedMsg;
        if (this.props.mode == "TEMPLATE") {
            savedMsg = "Diagram template saved.";
        } else {
            savedMsg = "Diagram saved.";
        }

        let toolsPanel;
        if (!this.state.readOnly) {
            toolsPanel = <div className="tools-controls d-print-none">
                <button className="btn btn-light btn-zoom-out"
                        data-container="body"
                        data-bs-toggle="tooltip"
                        data-bs-placement="left"
                        title="Zoom in"
                        onClick={this.handleZoomOut}>
                    <i className="bi bi-zoom-in"></i>
                </button>
                <button className="btn btn-light btn-zoom-in"
                        data-bs-toggle="tooltip"
                        data-bs-placement="left"
                        title="Zoom out"
                        onClick={this.handleZoomIn}>
                    <i className="bi bi-zoom-out"></i>
                </button>
                <button className="btn btn-light btn-zoom-fit"
                        data-bs-toggle="tooltip"
                        data-bs-placement="left"
                        title="Zoom diagram so it fits completely in current window."
                        onClick={this.onZoomToFit}>
                    <i className="bi bi-fullscreen"></i>
                </button>

                <div className="line-color-control ">
                    <button className="btn btn-light btn-fill"
                            data-bs-toggle="tooltip"
                            data-bs-placement="left"
                            title="Fill color for selected items"
                            onClick={this.handleLinePickerClick}>
                        <i className="bi bi-paint-bucket"></i>
                    </button>
                    {
                        this.state.displayLineColorPicker ?
                            <div className="color-picker-popover">
                                <div className="color-picker-cover"
                                     onClick={this.handleLinePickerClose}></div>
                                <TwitterPicker triangle="hide"
                                               color={this.state.currentLineColor}
                                               onChange={this.handleColorChange}/>
                            </div> : null
                    }

                    <button className="btn btn-light btn-duplicate"
                            data-bs-toggle="tooltip"
                            data-bs-placement="bottom"
                            title="Duplicate selected nodes."
                            onClick={this.onDuplicateSelected}>
                        <i className="bi bi-clipboard-plus"></i>
                    </button>

                </div>

            </div>
        }

        let controlBar;
        if (!this.state.readOnly) {
            controlBar = <div className="controls-bar d-print-none">
                <div className="controls-bar-left">


                    {
                        this.state.hasTemplate &&
                        <button className="btn btn-light btn-reset"
                                data-bs-toggle="tooltip"
                                data-bs-placement="top"
                                title="Reset diagram to initial template."
                                onClick={() => {
                                    if (window.confirm(
                                        'Are you sure you want to reset your diagram to the original template? ' +
                                        'You will loose any work you have completed.')) this.resetToTemplate()
                                }}>
                            <i className="bi bi-arrow-clockwise"></i>&nbsp;Reset
                        </button>
                    }


                </div>
                <div className="controls-bar-center">


                </div>
                <div className="controls-bar-right">
                    {this.state.sendInProgress ?
                        <div className="sit-saving-notice">
                            <div className="spinner-border" role="status">
                            </div>
                            &nbsp;Saving ...
                        </div> : null
                    }
                    <Toast className="sit-toast"
                           show={this.state.showSaveToast}
                           onClick={() => this.setState({showSaveToast: false})}
                           onClose={() => this.setState({showSaveToast: false})}
                           delay={1750}
                           autohide>
                        <Toast.Body><i className="bi bi-check"></i> {savedMsg}</Toast.Body>
                    </Toast>

                    <SITScores score={this.state.score} maxScore={this.state.maxScore} />
                    <OverlayTrigger
                        placement="top"
                        overlay={this.state.cannotSaveError ? <Tooltip>{this.state.cannotSaveError}</Tooltip> : <></>}
                    >
                        <span className="d-inline-block">
                            <button
                                className="btn btn-primary btn-save"
                                onClick={this.onSaveElements}
                                disabled={!this.state.hasChanges || !!this.state.cannotSaveError}
                            >
                                Save
                            </button>
                        </span>
                    </OverlayTrigger>
                </div>
            </div>
        }

        let trayInstructions;
        if (this.props.definition?.tray_instructions) {
            trayInstructions = <div className="tray-instructions text-muted">
                {this.props.definition.tray_instructions}
            </div>
        }

        let trayWidget;
        if (!this.state.readOnly) {
            trayWidget = <div className="tray-widget d-print-none">
                {getNodesForTrayNodesType(this.props.definition.tray_nodes_type).map(nodeType => (
                    <TrayItemWidget key={nodeType} mindMapType={nodeType}/>
                ))}
                {trayInstructions}
            </div>
        }

        return (
            <div ref={this.wrapperRef} className="sit-wrapper sit-diagramtool" onScroll={this.handleScroll}>
                <div className="content">
                    <div className="layer"
                         onDrop={this.onDropWidget}
                         onDragOver={this.onDragOver}>
                        <DiagramWidget engine={this.engine}/>
                    </div>
                    {trayWidget}
                </div>
                {controlBar}
                {toolsPanel}
            </div>
        );
    }
}

const DiagramWidget: VFC<{engine: DiagramEngine}> = ({ engine }) => {
    const [canvasWidget, setCanvasWidget] = useState<CanvasWidget | null>(null);

    useEffect(() => {
        const preventScroll = (event: WheelEvent) => {
            event.preventDefault();
            event.stopPropagation();

            const model = engine.getModel();
            const oldZoomFactor = model.getZoomLevel() / 100;

            const scrollDelta = event.deltaY / 60;
            const scrollModifier = event.ctrlKey ? 8 : 1;
            model.setZoomLevel(model.getZoomLevel() - (scrollDelta * scrollModifier));

            // Following logic/calculations come from the default ZoomCanvasAction by react-diagrams.
            if (targetIsElement(event.currentTarget)) {
                const zoomFactor = model.getZoomLevel() / 100;
                const boundingRect = event.currentTarget?.getBoundingClientRect();
                const clientWidth = boundingRect.width;
                const clientHeight = boundingRect.height;
                // compute difference between rect before and after scroll
                const widthDiff = clientWidth * zoomFactor - clientWidth * oldZoomFactor;
                const heightDiff = clientHeight * zoomFactor - clientHeight * oldZoomFactor;
                // compute mouse coords relative to canvas
                const clientX = event.clientX - boundingRect.left;
                const clientY = event.clientY - boundingRect.top;

                // compute width and height increment factor
                const xFactor = (clientX - model.getOffsetX()) / oldZoomFactor / clientWidth;
                const yFactor = (clientY - model.getOffsetY()) / oldZoomFactor / clientHeight;

                model.setOffset(model.getOffsetX() - widthDiff * xFactor, model.getOffsetY() - heightDiff * yFactor);
            }

            engine.repaintCanvas();
            return false;
        };

        // Make sure the scroll event is not passive, so we can manually cancel it.
        canvasWidget?.ref?.current?.addEventListener('wheel', preventScroll, { passive: false });

        // Hook cleanup.
        return () => canvasWidget?.ref?.current?.removeEventListener('wheel', preventScroll);
    }, [canvasWidget, engine])

    return (
        <DiagramCanvasWidget>
            <CanvasWidget
                ref={setCanvasWidget}
                engine={engine}
                className={`react-canvas ${engine.getModel().isLocked() ? 'readonly' : ''}`}
            />
        </DiagramCanvasWidget>
    )
}

function targetIsElement(target: any): target is Element {
    return !!(target as Element).getBoundingClientRect;
}
