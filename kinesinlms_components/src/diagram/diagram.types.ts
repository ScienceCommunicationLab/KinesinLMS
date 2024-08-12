export type DiagramToolDefinition = {
    // Props for all DIAGRAM types of SITs...
    tray_nodes_type: DiagramTrayNodesType;
    tray_instructions?: string;
    disable_link_strength: boolean;
} & (
    // Include different types depending on the tray_nodes_type.
    | DiagramToolGenericDefinitionProps
    | DiagramToolMentorCategoryDefinitionProps
    );

interface DiagramToolGenericDefinitionProps {
    tray_nodes_type: DiagramTrayNodesType.GENERIC;
}

interface DiagramToolMentorCategoryDefinitionProps {
    tray_nodes_type: DiagramTrayNodesType.MENTOR_CATEGORY;
    open_mentor_type_popup_after_add: boolean;
    can_save_without_mentor_type: boolean;
}

export function isDiagramToolMentorCategoryDefinitionProps(props: any): props is DiagramToolMentorCategoryDefinitionProps {
    return props.tray_nodes_type === DiagramTrayNodesType.MENTOR_CATEGORY;
}

export enum DiagramTrayNodesType {
    GENERIC = 'GENERIC',
    MENTOR_CATEGORY = 'MENTOR_CATEGORY',
}
