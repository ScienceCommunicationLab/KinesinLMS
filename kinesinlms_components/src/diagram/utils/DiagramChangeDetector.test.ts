import DiagramChangeDetector from './DiagramChangeDetector';
import { DiagramModel } from '@projectstorm/react-diagrams';

describe('DiagramChangeDetector', () => {
    it('should never have changes without changing the model content', function () {
        const model = new DummyModel();
        model.content = { foo: 'bar' };

        const checker = new DiagramChangeDetector(model  as unknown as DiagramModel);

        // Without changing the content, the model should never have changes.
        expect(checker.hasChanges().hasSoftChanges).toBe(false);
        expect(checker.hasChanges().hasHardChanges).toBe(false);
    });

    it('should ignore properties on the blacklist on root level', () => {
        const model = new DummyModel();
        model.content = { selected: true };

        const checker = new DiagramChangeDetector(model  as unknown as DiagramModel);

        model.content = { selected: false };
        expect(checker.hasChanges().hasSoftChanges).toBe(false);
        expect(checker.hasChanges().hasHardChanges).toBe(false);
    });

    it('should have changes if there are extra changes on fields not on the blacklist', () => {
        const model = new DummyModel();
        model.content = { selected: true, other: 'prop' };

        const checker = new DiagramChangeDetector(model  as unknown as DiagramModel);

        model.content = { selected: false, other: 'different prop' };
        expect(checker.hasChanges().hasSoftChanges).toBe(true);
        expect(checker.hasChanges().hasHardChanges).toBe(true);
    });

    it('should not have changes if there are extra props not on the blacklist but no changes on them', () => {
        const model = new DummyModel();
        model.content = { selected: true, other: 'prop' };

        const checker = new DiagramChangeDetector(model  as unknown as DiagramModel);

        model.content = { selected: false, other: 'prop' };
        expect(checker.hasChanges().hasSoftChanges).toBe(false);
        expect(checker.hasChanges().hasHardChanges).toBe(false);
    });

    it('should not have changes if a nested property changes but is on the blacklist', () => {
        const model = new DummyModel();
        model.content = {
            nested: {
                selected: true,
            },
        };

        const checker = new DiagramChangeDetector(model  as unknown as DiagramModel);

        model.content = {
            nested: {
                selected: false
            }
        };
        expect(checker.hasChanges().hasSoftChanges).toBe(false);
        expect(checker.hasChanges().hasHardChanges).toBe(false);
    });

    it('should not have changes if a blacklisted property is added', () => {
        const model = new DummyModel();
        model.content = {
            foo: 'bar',
        };

        const checker = new DiagramChangeDetector(model  as unknown as DiagramModel);

        model.content = {
            foo: 'bar',
            selected: true,
        };
        expect(checker.hasChanges().hasSoftChanges).toBe(false);
        expect(checker.hasChanges().hasHardChanges).toBe(false);
    });

    it('should not have changes if a blacklisted property is removed', () => {
        const model = new DummyModel();
        model.content = {
            foo: 'bar',
            selected: true,
        };

        const checker = new DiagramChangeDetector(model  as unknown as DiagramModel);

        model.content = {
            foo: 'bar',
        };
        expect(checker.hasChanges().hasSoftChanges).toBe(false);
        expect(checker.hasChanges().hasHardChanges).toBe(false);
    });

    it('should only have soft changes if a not-so-important property is changed', () => {
        const model = new DummyModel();
        model.content = { zoom: 100 };

        const checker = new DiagramChangeDetector(model  as unknown as DiagramModel);

        model.content = { zoom: 110 };
        expect(checker.hasChanges().hasSoftChanges).toBe(true);
        expect(checker.hasChanges().hasHardChanges).toBe(false);
    });
});

class DummyModel {
    public content!: object;

    serialize() {
        return this.content;
    }
}
