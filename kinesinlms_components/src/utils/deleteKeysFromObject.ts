import _ from 'lodash';

/**
 * Recursively removes keys from a deep object.
 *
 * Example input: { a: 1, x: { a: 2, b: 3 } }
 * Example output: { x: { b: 3 } }
 */
function deleteKeysFromObject<T extends { [key: string]: unknown }>(obj: T, keysToDelete: string[]) {
    const clonedObj = _.cloneDeep(obj);
    deleteKeys<T>(clonedObj, keysToDelete);
    return clonedObj;
}

/**
 * Private function that deletes the keys by reference.
 * Should be executed on a cloned object in the public function(s).
 */
function deleteKeys<T extends { [key: string]: unknown }>(obj: T, keysToDelete: string[]) {
    for (const key in obj) {
        if (keysToDelete.includes(key)){
            delete obj[key];
        }
        else if (typeof obj[key] === 'object') {
            deleteKeys(obj[key] as T, keysToDelete);
        }
    }
}

export default deleteKeysFromObject;
