// @ts-ignore
import React, { useEffect, useState, VFC } from 'react';
import { TableToolDefinition, TableToolSubmissionRow } from './TableTool.types';
import EditableTableTool from './components/EditableTableTool';
import SaveButton from './components/SaveButton';
import AddRowButton from './components/AddRowButton';
import SavingNotice from './components/SavingNotice';
import SavedToast from './components/SavedToast';
import useSaveTable from './hooks/useSaveTable';
import useTable from './hooks/useTable';
import { ControlsBar } from './TableTool.styles';
import SITScores from '../SITScores';

// Props that we do not use, but still come from the server, are commented out.
interface Props {
    course_id: number;
    course_unit_id: number;
    // course_unit_slug: string;
    definition: TableToolDefinition;
    existing_simple_interactive_tool_submission?: TableToolSubmissionRow[];
    existing_simple_interactive_tool_submission_id?: number;
    // has_template: boolean;
    // is_template: boolean;
    // mode: "BASIC";
    read_only: boolean;
    simple_interactive_tool_id: number;
    score: number;
    max_score: number;
    // status: "Unanswered";
    // tool_type: "TABLETOOL";
}

const TableTool: VFC<Props> = ({
    course_id,
    course_unit_id,
    definition,
    existing_simple_interactive_tool_submission: initialSubmission,
    existing_simple_interactive_tool_submission_id: initialSubmissionId,
    read_only,
    simple_interactive_tool_id,
    score,
    max_score,
}) => {
    const [submissions, setSubmissions] = useState(initialSubmission ?? []);
    const [submissionId, setSubmissionId] = useState(initialSubmissionId);
    const [_, setScore] = useState(score);

    const [saving, setSaving] = useState(false);
    const [showSavedMessage, setShowSavedMessage] = useState(false);
    const [isSaved, setIsSaved] = useState(false);

    const {
        headers,
        rows,
        submissionRows,
        canAddEmptyRow,
        addEmptyRow,
        isDirty,
    } = useTable({
        columnDefinitions: definition.column_definitions,
        defaultRows: definition.default_rows,
        initialSubmissionRows: submissions,
        canAddRows: definition.allow_add_row,
        canRemoveRows: definition.allow_remove_row,
        minRows: definition.initial_empty_rows,
        maxRows: definition.max_rows,
        isReadOnly: read_only,
        maxScore: max_score,
    });

    const saveTable = useSaveTable({
        canSave: !read_only,
        submissionId: submissionId,
        onBeforeSave: () => {
            setShowSavedMessage(false);
            setSaving(true);
        },
        onSuccess: (savedRows, submissionId, score) => {
            setSubmissions(savedRows ?? []);
            setSubmissionId(submissionId);
            setScore(score);
            setSaving(false);
            setShowSavedMessage(true);
            setIsSaved(true);
        },
        onFailure: () => {
            setSaving(false);
            setShowSavedMessage(false);
        },
    });

    useEffect(() => {
        const handleBeforeUnload = (event: BeforeUnloadEvent) => {
            if (!isSaved && isDirty) {
                event.returnValue = true;
                return true;
            }
        };
        window.addEventListener('beforeunload', handleBeforeUnload);
        return () => window.removeEventListener('beforeunload', handleBeforeUnload);
    }, [isDirty, isSaved]);

    const handleSave = () => {
        saveTable(simple_interactive_tool_id, course_unit_id, course_id, submissionRows);
    };

    const showSaveButton = !read_only;

    return (
        <div className="sit-wrapper tabletool-wrapper">
            <div className="content">
                <EditableTableTool headers={headers} rows={rows} />
                {!read_only && canAddEmptyRow && <AddRowButton onAdd={addEmptyRow} canAdd={!saving}/>}
            </div>
            <ControlsBar
                hasNoActions={!showSaveButton}
                className="controls-bar d-print-none"
            >
                <div className="controls-bar-left"></div>
                <div className="controls-bar-center "></div>
                <div className="controls-bar-right">
                    <SavedToast isVisible={showSavedMessage} handleClose={() => setShowSavedMessage(false)}/>
                    {saving && <SavingNotice/>}
                    <SITScores score={score} maxScore={max_score} />
                    {showSaveButton && <SaveButton onSave={handleSave} canSave={!saving && isDirty}/>}
                </div>
            </ControlsBar>
        </div>
    )
};

export default TableTool;
