import { DiagramModel } from '@projectstorm/react-diagrams';
import stringify from 'fast-json-stable-stringify'
import { create as createJsonDiffPatcher, DiffPatcher } from 'jsondiffpatch';

export default class DiagramChangeDetector {
    private readonly normalizedInitialModel: object;
    private readonly jsonPatcherWithSoftChanges: DiffPatcher;
    private readonly jsonPatcherWithHardChanges: DiffPatcher;

    constructor(private readonly model: DiagramModel) {
        this.normalizedInitialModel = this.getNormalizedModel(model);

        const softChangesBlacklist = ['selected'];
        const hardChangesBlacklist = [...softChangesBlacklist, 'offsetX', 'offsetY', 'zoom'];

        this.jsonPatcherWithSoftChanges = createJsonDiffPatcher({
            propertyFilter: (name: string) => !softChangesBlacklist.includes(name),
        });
        this.jsonPatcherWithHardChanges = createJsonDiffPatcher({
            propertyFilter: (name: string) => !hardChangesBlacklist.includes(name),
        });
    }

    // TODO: when diagram.tsx is refactored and uses functional components, we can move this
    //  functionality to a hook and make it 'master' from the isDirty state itself.
    //  That way we will not have to manually call the check function anymore (=imperative),
    //  but the data will be reactive.
    public hasChanges(): {
        /** For hard changes, we will ask the user to confirm the changes before leaving a page. */
        hasHardChanges: boolean;
        /** The user should be able to save soft changes, but we would not show any popups to remind the user to save. */
        hasSoftChanges: boolean;
    } {
        const normalizedModel = this.getNormalizedModel(this.model);

        const softChangesDelta = this.jsonPatcherWithSoftChanges.diff(this.normalizedInitialModel, normalizedModel);
        const hardChangesDelta = this.jsonPatcherWithHardChanges.diff(this.normalizedInitialModel, normalizedModel);

        console.log('diagram soft changes:', softChangesDelta);
        console.log('diagram hard changes:', hardChangesDelta);

        return {
            hasSoftChanges: !!softChangesDelta,
            hasHardChanges: !!hardChangesDelta,
        };
    }

    /**
     * * The return value is not an actual DiagramModel anymore, but rather a more simple
     * object that contains all public props of the DiagramModel. Has the values that
     * are actually saved in the backend, but only those values and nothing more.
     */
    private getNormalizedModel(model: DiagramModel): object {
        const serializedModel = model.serialize();
        // The model properties are now sorted to make sure results are always the same.
        const stringifiedModel = stringify(serializedModel);
        return JSON.parse(stringifiedModel);
    }
}
