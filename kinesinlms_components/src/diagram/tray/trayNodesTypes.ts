import { CustomNodeTypes } from '../custom-node/CustomNodeTypes';
import { DiagramTrayNodesType } from '../diagram.types';

export const defaultTrayNodesType = DiagramTrayNodesType.GENERIC;

const trayNodesTypesMap: {[key in DiagramTrayNodesType]: CustomNodeTypes[]} = {
    [DiagramTrayNodesType.GENERIC]: [CustomNodeTypes.BASIC],
    [DiagramTrayNodesType.MENTOR_CATEGORY]: [CustomNodeTypes.PERSON, CustomNodeTypes.CATEGORY],
}

export function getNodesForTrayNodesType(type: DiagramTrayNodesType): CustomNodeTypes[] {
    if (Object.values(DiagramTrayNodesType).includes(type)) {
        return trayNodesTypesMap[type];
    }
    return trayNodesTypesMap[defaultTrayNodesType];
}
