import { useCallback } from 'react';
import { TableToolSubmissionRow } from '../TableTool.types';
import axios, { Method } from 'axios';

interface UseSaveTableOpts {
    canSave: boolean;
    submissionId: number | undefined;
    onBeforeSave?: () => void;
    onSuccess?: (savedRows: TableToolSubmissionRow[], submissionId: number, score:number) => void;
    onFailure?: (error: any) => void;
}

function useSaveTable({
    canSave,
    submissionId,
    onBeforeSave,
    onSuccess,
    onFailure,
}: UseSaveTableOpts) {
    return useCallback((
        simpleInteractiveToolId: number,
        courseUnitId: number,
        courseId: number,
        rows: TableToolSubmissionRow[],
    ) => {
        if (!canSave) {
            return;
        }

        onBeforeSave?.();

        /* Set up constants and defaults for Axios */
        axios.defaults.xsrfCookieName = 'csrftoken';
        axios.defaults.xsrfHeaderName = 'X-CSRFToken';

        const simpleInteractiveToolSubmissionJSON = {
            simple_interactive_tool: simpleInteractiveToolId,
            course_unit: courseUnitId,
            course: courseId,
            json_content: rows,
        };
        let requestMethod: Method = "post";
        let targetURL = "/api/simple_interactive_tool_submissions/";
        if (!!submissionId) {
            requestMethod = "put";
            targetURL = "/api/simple_interactive_tool_submissions/" + submissionId + "/";
        }
        const config = {
            url: targetURL,
            data: simpleInteractiveToolSubmissionJSON,
            withCredentials: true,
            method: requestMethod
        }
        axios.request(config)
            .then((response) => {
                console.log("Tabletool: received response from server: ", response);
                onSuccess?.(rows, response.data.id, response.data.score);
            })
            .catch((error) => {
                console.log("Save error: ", error);
                onFailure?.(error);
                if (error.response && error.response.data) {
                    const responseData = error.response.data;
                    let errorMessage = '';
                    if (responseData.detail) {
                        errorMessage = responseData.detail;
                    }
                    if (responseData.non_field_errors) {
                        errorMessage = errorMessage + ". " + responseData.non_field_errors.join(', ');
                    }
                    window.alert(`Could not save table data. ${errorMessage}`);
                } else {
                    window.alert(`Could not save table data.`);
                }
            });
    }, [canSave, onBeforeSave, onSuccess, onFailure]);
}

export default useSaveTable;
