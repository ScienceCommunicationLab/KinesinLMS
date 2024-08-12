import { DiagramTrayNodesType } from '../diagram.types';
import { getNodesForTrayNodesType } from './trayNodesTypes';
import { CustomNodeTypes } from '../custom-node/CustomNodeTypes';

describe('trayNodesTypes', () => {
    describe('getNodesForTrayNodesType', () => {
        it('should return the correct types for GENERIC as an enum', () => {
            const type = DiagramTrayNodesType.GENERIC;
            const nodes = getNodesForTrayNodesType(type);
            expect(nodes).toEqual([CustomNodeTypes.BASIC]);
        });

        it('should return the correct types for GENERIC as a string', () => {
            const type = 'GENERIC' as DiagramTrayNodesType;
            const nodes = getNodesForTrayNodesType(type);
            expect(nodes).toEqual([CustomNodeTypes.BASIC]);
        });

        it('should return the correct types for MENTOR_CATEGORY as an enum', () => {
            const type = DiagramTrayNodesType.MENTOR_CATEGORY;
            const nodes = getNodesForTrayNodesType(type);
            expect(nodes).toEqual([CustomNodeTypes.PERSON, CustomNodeTypes.CATEGORY]);
        });

        it('should return the correct types for MENTOR_CATEGORY as a string', () => {
            const type = 'MENTOR_CATEGORY' as DiagramTrayNodesType;
            const nodes = getNodesForTrayNodesType(type);
            expect(nodes).toEqual([CustomNodeTypes.PERSON, CustomNodeTypes.CATEGORY]);
        });

        it('should return the GENERIC values if the type is not known', () => {
            const type = 'invalid_value' as DiagramTrayNodesType;
            const nodes = getNodesForTrayNodesType(type);
            expect(nodes).toEqual([CustomNodeTypes.BASIC]);
        });

        it('should return the GENERIC values if the type is empty', () => {
            const type = undefined as unknown as DiagramTrayNodesType;
            const nodes = getNodesForTrayNodesType(type);
            expect(nodes).toEqual([CustomNodeTypes.BASIC]);
        });
    });
});
