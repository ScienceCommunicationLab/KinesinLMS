/******/ (function() { // webpackBootstrap
/******/ 	"use strict";
var __webpack_exports__ = {};
// This entry need to be wrapped in an IIFE because it uses a non-standard name for the exports (exports).
!function() {
var exports = __webpack_exports__;
/*!*******************************************!*\
  !*** ./kinesinlms/static/src/composer.ts ***!
  \*******************************************/

// Javascript for the composer app.
// Note that it's assumed project.js will always be present and loaded before
// this file, so we don't need to include here the libraries and styles
// that are imported in project.js.
Object.defineProperty(exports, "__esModule", ({ value: true }));
// Set up HTMX for composer
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/**
 *  Set up HTMX for composer.
 */
document.body.addEventListener('htmx:configRequest', (event) => {
    if (!event) {
        console.error("htmx:configRequest event is null", event);
        return;
    }
    const customEvent = event;
    const blockID = customEvent.detail.target.id;
    if (blockID.includes("block-edit-form-") || blockID.includes("course-unit-block-")) {
        // If this block has HTML_CONTENT or QUESTION_TEXT fields in it,
        // and WYSIWYG is enabled, we need to make sure to run TinyMCE
        // so that it collects rich text before calling the API.
        if (!tinyMCE || !tinyMCE.activeEditor) {
            console.log("We're editing raw HTML so no need to copy content from TinyMCE...");
            return;
        }
        console.log("Copying content from TinyMCE before making HTMx request...");
        const inputVarNames = ["html_content", "question_text"];
        inputVarNames.forEach(inputVarName => {
            const customEvent = event;
            if (customEvent.detail && inputVarName in customEvent.detail.parameters) {
                // Get the rich HTML and use it to replace the plain
                // text that currently exists in the outgoing request...
                const inputID = `id_${inputVarName}`;
                const richContentEditor = tinyMCE.get(inputID);
                if (!richContentEditor) {
                    console.error(`Could not find element with ID ${inputID}`);
                    return;
                }
                customEvent.detail.parameters[inputVarName] = richContentEditor.getContent();
            }
        });
    }
});
// Set up Alpine data stores for composer
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/** Set up Alpine data stores for composer. */
document.addEventListener('alpine:init', () => {
    Alpine.store('isEditingBlock', false);
    Alpine.store('isEditingCourseUnitInfo', false);
    console.log("Alpine init");
});
// Composer events
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/**
 * Listen for HTMx event that a course unit's "info" form is
 * being edited. When this happens we want to disable other controls
 * on the page.
 */
document.body.addEventListener('editCourseUnitInfoActivated', function (evt) {
    console.log("editCourseUnitInfoActivated", evt);
    Alpine.store('isEditingCourseUnitInfo', true);
    klmsToggleDisableReadOnlyBlockControls(true);
});
document.body.addEventListener('editCourseUnitInfoDeactivated', function (evt) {
    console.log("editCourseUnitInfoDeactivated", evt);
    Alpine.store('isEditingCourseUnitInfo', false);
    klmsToggleDisableReadOnlyBlockControls(false);
});
/**
 * Listen for HTMx event that indicates a block is
 * being edited in a block edit panel. When this happens we want to disable
 * other controls on the page.
 */
document.body.addEventListener('editBlockPanelActivated', function (evt) {
    Alpine.store('isEditingBlock', true);
    console.log("editBlockPanelActivated", evt);
    const eventDetail = evt.detail;
    klmsInitPanelForm(eventDetail.block_id, eventDetail.current_panel_slug);
    klmsToggleDisableReadOnlyBlockControls(true);
});
/**
 * Listen for HTMx event that indicates a block is
 * no longer being edited. When this happens we want to enable
 * other controls on the page.
 */
document.body.addEventListener('editBlockPanelDeactivated', function (evt) {
    Alpine.store('isEditingBlock', false);
    klmsToggleDisableReadOnlyBlockControls(false);
});
/**
 *
 * klmsToggleDisableReadOnlyBlockControls()
 *
 * Toggle the disabled state and visual style of controls for read-only blocks.
 *
 * We do this when a block is being edited in a panel, and we want to turn off
 * all other controls so the user can focus on the block they're editing (and
 * the other controls don't get the page into a bad state).
 *
 * @param isDisabled - Boolean indicating whether to disable or enable the controls.
 *
 */
function klmsToggleDisableReadOnlyBlockControls(isDisabled = false) {
    console.log("Disabling read-only block controls: ", isDisabled);
    // Disable course unit info controls
    const editCourseUnitInfoButton = document.getElementById("btn-edit-course-unit-info");
    if (editCourseUnitInfoButton) {
        editCourseUnitInfoButton.classList.toggle("disabled", isDisabled);
    }
    // Disable toggle WYSIWYG button
    const toggleWYSIWYGButton = document.getElementById("btn-toggle-wysiwyg");
    if (toggleWYSIWYGButton) {
        toggleWYSIWYGButton.classList.toggle("disabled", isDisabled);
    }
    // Disable add block buttons
    const addBlockAtEndButton = document.getElementById("btn-add-block-end");
    if (addBlockAtEndButton) {
        console.log("Disabling add block at end button: ", addBlockAtEndButton);
        addBlockAtEndButton.classList.toggle("disabled", isDisabled);
    }
    const addBlockButtons = document.querySelectorAll(".connector-add-block-button");
    addBlockButtons.forEach(button => {
        console.log("Disabling add block button: ", button);
        button.classList.toggle("disabled", isDisabled);
    });
    // Disable all header controls in read-only blocks.
    const readOnlyBlocks = document.querySelectorAll(".block-edit-card-read-only");
    readOnlyBlocks.forEach(block => {
        const querySelectors = [
            ".btn-block-edit",
            ".btn-block-delete",
            ".btn-block-move-up",
            ".btn-block-move-down",
            ".connector-add-block-button",
        ];
        querySelectors.forEach(selector => {
            const control = block.querySelector(selector);
            if (control) {
                console.log("Disabling control: ", control);
                control.classList.toggle("disabled", isDisabled);
            }
        });
    });
}
/*
* klmsUpdateTextWithNewImageURL()
* If the user has dragged an image onto the editor, and we have
* successfully create a new CourseResource on the server, it's time
* to update the content in the editor with an image tag pointing to the
* newly created resouce.
* We have to do this in either raw HTML or TinyMCE, depending on which
* is currently active.
*/
function klmsUpdateTextWithNewImageURL(imageURL) {
    console.log("klmsUpdateTextWithNewImageURL: ", imageURL);
    const newImageTag = `<img src="${imageURL}" alt="image" />`;
    // We need a ref to the raw HTML textarea regardless of whether
    // it or TinyMCE is active...
    const htmlContentTAElem = document.getElementById(`id_html_content`);
    // Update either TinyMCE or raw HTML textarea with new image tag.
    if (tinyMCE && tinyMCE.activeEditor) {
        console.log("TinyMCE is active. Updating with img tag...");
        const activeEditor = tinyMCE.activeEditor;
        const cursorPos = activeEditor.selection.getRng();
        activeEditor.selection.setContent(newImageTag);
        console.log("Dispatching 'change' event from ", activeEditor);
    }
    else {
        console.log("Raw HTML textarea is active. Updating with img tag...");
        if (!htmlContentTAElem) {
            return;
        }
        const cursorPos = htmlContentTAElem.selectionStart;
        const textBefore = htmlContentTAElem.value.substring(0, cursorPos);
        const textAfter = htmlContentTAElem.value.substring(cursorPos);
        htmlContentTAElem.value = `${textBefore}\n${newImageTag}\n${textAfter}`;
    }
    // Regardless of whether we're in TinyMCE or raw HTML, we need to
    // dispatch a change event so that the form knows the content has changed.
    console.log("Dispatching 'change' event from ", htmlContentTAElem);
    // That change event should cause the Save/Done buttons to toggle
    htmlContentTAElem.dispatchEvent(new Event('change', { bubbles: true }));
}
function klmsUploadCourseResourceFile(file, courseID, blockID) {
    console.log("klmsUploadCourseResourceFile: ", file, courseID, blockID);
    const formData = new FormData();
    formData.append('resource_file', file);
    formData.append('type', 'IMAGE');
    // AJAX request to upload file
    const xhr = new XMLHttpRequest();
    // Extract CSRF token from the body tag's hx-headers attribute.
    // We set it there for HTMx, and although we're not doing an HTMx
    // request here, we can still get the token from the same place.
    const csrfToken = document.body.getAttribute('hx-headers');
    let token = '';
    if (csrfToken) {
        try {
            const headers = JSON.parse(csrfToken);
            token = headers['X-CSRFToken'] || '';
        }
        catch (e) {
            console.error('Failed to parse CSRF token:', e);
        }
    }
    console.log("csrfToken: ", csrfToken);
    const uploadURL = `/composer/course/${courseID}/block/${blockID}/upload_course_resource/`;
    xhr.open('POST', uploadURL, true);
    xhr.setRequestHeader('X-CSRFToken', token);
    const errMessage = 'Error occurred during upload. Please try again, or manually add the resource on the "Resources" tab.';
    xhr.onload = function () {
        if (xhr.status === 201) {
            const response = JSON.parse(xhr.responseText);
            console.log("Upload successful: ", xhr.responseText);
            const imageURL = response.resource_url;
            klmsUpdateTextWithNewImageURL(imageURL);
        }
        else {
            window.alert(errMessage);
            console.error('Upload failed:', xhr.status);
        }
    };
    xhr.onerror = function () {
        window.alert(errMessage);
    };
    xhr.send(formData);
}
function klmsHTMLContentOnDragEnter(event) {
    console.log("klmsHTMLContentOnDragEnter");
    event.preventDefault();
    event.stopPropagation();
    const dropZoneElem = document.getElementById("image_drop_zone");
    if (!dropZoneElem) {
        return;
    }
    dropZoneElem.classList.add('drag-drop-highlight');
}
function klmsHTMLContentOnDragOver(event) {
    console.log("klmsHTMLContentOnDragOver");
    event.preventDefault();
    event.stopPropagation();
    const dropZoneElem = document.getElementById("image_drop_zone");
    if (!dropZoneElem) {
        return;
    }
    dropZoneElem.classList.add('drag-drop-highlight');
}
function klmsHTMLContentOnDragLeave(event) {
    console.log("klmsHTMLContentOnDragLeave");
    event.preventDefault();
    event.stopPropagation();
    const dropZoneElem = document.getElementById("image_drop_zone");
    if (!dropZoneElem) {
        return;
    }
    dropZoneElem.classList.remove('drag-drop-highlight');
}
function klmsHTMLContentOnDrop(event) {
    console.log("klmsHTMLContentOnDrop");
    event.preventDefault();
    event.stopPropagation();
    const dropZoneElem = document.getElementById("image_drop_zone");
    if (!dropZoneElem) {
        return;
    }
    dropZoneElem.classList.remove('drag-drop-highlight');
    console.log("dropZoneElem: ", dropZoneElem);
    console.log("dropZoneElem.dataset: ", dropZoneElem.dataset);
    const courseID = dropZoneElem.dataset.courseId;
    const blockID = dropZoneElem.dataset.blockId;
    console.log("drop event. blockID: ", blockID);
    console.log("drop event. blockIcourseIDD: ", courseID);
    const dt = event.dataTransfer;
    if (dt && courseID && blockID) {
        const files = dt.files;
        console.log("files: ", files);
        Array.from(files).forEach(file => {
            console.log("uploading file: ", file);
            klmsUploadCourseResourceFile(file, courseID, blockID);
        });
    }
}
/*
*
* initComposerImageDropZone()
*
* Allow the author to drag and drop images into the composer
* textarea. This action will
* 1) upload image and create a CourseResource instance
* and
* 2) have the image URL automatically added to the html content.
*
*/
function klmsInitComposerImageDropZone() {
    const dropZoneElem = document.getElementById("image_drop_zone");
    if (!dropZoneElem) {
        // This panel probs doesn't have an HTML Content field and the
        // accompanying drop zone.
        return;
    }
    // Remove any existing event listeners
    dropZoneElem.removeEventListener("dragenter", klmsHTMLContentOnDragEnter, false);
    dropZoneElem.removeEventListener("dragover", klmsHTMLContentOnDragOver, false);
    dropZoneElem.removeEventListener("dragleave", klmsHTMLContentOnDragLeave, false);
    dropZoneElem.removeEventListener("drop", klmsHTMLContentOnDrop, false);
    // Prevent default drag behaviors
    dropZoneElem.addEventListener("dragenter", klmsHTMLContentOnDragEnter, false);
    dropZoneElem.addEventListener("dragover", klmsHTMLContentOnDragOver, false);
    dropZoneElem.addEventListener("dragleave", klmsHTMLContentOnDragLeave, false);
    dropZoneElem.addEventListener("drop", klmsHTMLContentOnDrop, false);
}
/* Panels */
// TODO: Break out into separate modules and/or classes
/**
 * klmsInitPanelForm()
 *
 * This function is called when a panel for editing a block has been
 * loaded via an HTMx call and is now being activated.
 *
 * It initializes the panel's form and sets up event listeners
 * to manage the "Save" and "Done" buttons disabled states, as well as the disabled
 * state of the tabs in the panel set.
 *
 * This is all in an effort to keep a user on a particular
 * pane AND tab until they've saved their work.
 */
function klmsInitPanelForm(blockID, currentPanelSlug) {
    // Get reference to form and submit button
    const panelFormID = `panel-form-${blockID}-${currentPanelSlug}`;
    const panelForm = document.getElementById(panelFormID);
    if (!panelForm) {
        console.error("Could not find DOM element", panelFormID);
        return;
    }
    // Remove existing event listeners to avoid duplication
    panelForm.removeEventListener('change', onPanelFormChange);
    panelForm.removeEventListener('wysiwyg_change', onPanelFormChange);
    // Some panels do not certain buttons, like the "Save" button.
    const submitButtonID = `btn-save-panel-${blockID}-${currentPanelSlug}`;
    const submitButton = document.getElementById(submitButtonID);
    if (submitButton) {
        // Disable the submit button initially
        submitButton.disabled = true;
    }
    else {
        console.info("Could not find DOM element", submitButtonID);
    }
    const doneButtonID = `btn-done-panel-${blockID}-${currentPanelSlug}`;
    const doneButton = document.getElementById(doneButtonID);
    if (doneButton) {
        console.info("Could not find DOM element", doneButtonID);
    }
    const cancelButtonID = `btn-cancel-panel-${blockID}-${currentPanelSlug}`;
    const cancelButton = document.getElementById(cancelButtonID);
    if (!cancelButton) {
        console.info("Could not find DOM element", cancelButtonID);
    }
    // Serialize initial form data
    const initialFormData = new URLSearchParams(new FormData(panelForm));
    function onPanelFormChange(event) {
        console.log("Panel form changed! event: ", event);
        // If user is using raw HTML content, we check to see if content has changed.
        // But if they're using TinyMCE...not sure yet how to check for changes, so just assume
        // content is different.
        let hasChanged = true;
        if (tinyMCE && tinyMCE.activeEditor) {
            // Leave hasChanged as true. We'll always assume content has changed.
        }
        else {
            const currentFormData = new URLSearchParams(new FormData(panelForm));
            hasChanged = currentFormData.toString() !== initialFormData.toString();
        }
        // Enable/disable submit button based on form changes
        if (submitButton) {
            submitButton.disabled = !hasChanged;
            submitButton.classList.toggle("d-none", !hasChanged);
            if (hasChanged) {
                submitButton.focus();
            }
        }
        if (doneButton) {
            doneButton.disabled = hasChanged;
            doneButton.classList.toggle("d-none", hasChanged);
        }
        if (cancelButton) {
            cancelButton.classList.toggle("d-none", !hasChanged);
        }
        // Enable/disable tabs on panelset
        const buttons = document.querySelectorAll(`#panel-navs-${blockID} button.nav-link`);
        // Loop through each button and set the 'disabled' attribute
        buttons.forEach(button => {
            button.disabled = hasChanged;
        });
    }
    // Check for changes in the form fields. When there's a change
    // update the various UI elements in the panel and panel set accordingly.
    panelForm.addEventListener('change', onPanelFormChange, false);
    panelForm.addEventListener('wysiwyg_change', onPanelFormChange, false);
    klmsInitComposerImageDropZone();
}
function klmsDestroyCurrentPanelForm() {
    console.log("klmsDestroyCurrentPanelForm()");
    if (tinyMCE) {
        console.log("Destroying TinyMCE...");
        tinyMCE.remove();
    }
}
window.klmsInitComposerImageDropZone = klmsInitComposerImageDropZone;
window.klmsHTMLContentOnDragEnter = klmsHTMLContentOnDragEnter;
window.klmsHTMLContentOnDragOver = klmsHTMLContentOnDragOver;
window.klmsHTMLContentOnDragLeave = klmsHTMLContentOnDragLeave;
window.klmsHTMLContentOnDrop = klmsHTMLContentOnDrop;
window.klmsDestroyCurrentPanelForm = klmsDestroyCurrentPanelForm;

}();
/******/ })()
;
//# sourceMappingURL=kinesinlms-composer.bundle.js.map