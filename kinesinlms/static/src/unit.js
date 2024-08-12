// Scripts used in Unit pages


function klmsToggleBlockFullScreen(expandBlockElem, showFullScreen) {

    //Toggle course nav and subnav
    const unitTitle = document.getElementById("unit-title-container");
    const unitHTML = document.getElementById("unit-html-content");
    const courseSubNav = document.getElementById("course-subnav-wrapper");
    const courseLicense = document.getElementById("course-license-wrapper");
    const footer = document.getElementById("footer-wrapper");
    const adminControls = document.getElementById('admin-controls-wrapper')
    const standAloneBlockInfo = document.getElementById('stand-alone-block-info');
    const els = [unitTitle, unitHTML, courseSubNav, courseLicense, footer, adminControls, standAloneBlockInfo]
    els.forEach(el => {
        if (el) {
            if (showFullScreen) {
                el.classList.add('d-none');
            } else {
                el.classList.remove('d-none');
            }
        }

    })

    // Toggle margin on unit-content
    const unitContent = document.getElementById("unit-title-container");
    if (unitContent) {
        if (showFullScreen) {
            unitContent.classList.add('mb-0');
        } else {
            unitContent.classList.remove('mb-3');
        }
    }

    // Toggle infobars
    const courseInfoBars = document.querySelectorAll(".course-info-bar-wrapper");
    if (courseInfoBars) {
        courseInfoBars.forEach(courseInfoBar => {
            if (showFullScreen) {
                courseInfoBar.classList.add("d-none"); //add bootstrap hide class.
            } else {
                courseInfoBar.classList.remove("d-none"); //add bootstrap hide class.
            }
        })
    }


    //Toggle container 'fluid'
    const courseUnitContainer = document.getElementById('course-unit-container');
    if (showFullScreen) {
        courseUnitContainer.classList.remove('container');
        courseUnitContainer.classList.add('container-fluid');
    } else {
        courseUnitContainer.classList.add('container');
        courseUnitContainer.classList.remove('container-fluid');
    }


    //Toggle all blocks except the one we're expanding...
    const query = `.block:not(#${expandBlockElem.id})`;
    const unitBlocks = document.querySelectorAll(query);
    if (unitBlocks) {
        unitBlocks.forEach(unitBlock => {
            if (showFullScreen) {
                unitBlock.classList.add("d-none"); //add bootstrap hide class.
            } else {
                unitBlock.classList.remove("d-none"); //add bootstrap hide class.
            }
        })
    }


    //Toggle any other "Unit" page content we don't want to show
    const unitTitleContainer = document.getElementById("unit-title-container")
    if (unitTitleContainer) {
        if (showFullScreen) {
            unitTitleContainer.classList.add("d-none"); //add bootstrap hide class.
        } else {
            unitTitleContainer.classList.remove("d-none"); //add bootstrap hide class.
        }
    }

    // Toggle diagram content back to 'full screen' view
    const showBlockElements = expandBlockElem.querySelectorAll('.block-embedded-content');
    if (showBlockElements) {
        showBlockElements.forEach(unitBlock => {
            if (showFullScreen) {
                unitBlock.classList.add("d-none"); //add bootstrap hide class.
            } else {
                unitBlock.classList.remove("d-none"); //add bootstrap hide class.
            }
        });
    }


    const hideBlockElements = expandBlockElem.querySelectorAll('.block-fullscreen-content');
    if (hideBlockElements) {
        hideBlockElements.forEach(unitBlock => {
            if (showFullScreen) {
                unitBlock.classList.remove("d-none"); //add bootstrap hide class.
            } else {
                unitBlock.classList.add("d-none"); //add bootstrap hide class.
            }
        })
    }

    // Make diagram full height
    if (showFullScreen) {
        expandBlockElem.classList.add("block-fullscreen");
    } else {
        expandBlockElem.classList.remove("block-fullscreen");
    }


}

function klmsOnBlockToFullScreen(expandBlockID) {
    const expandBlockElem = document.getElementById(expandBlockID);
    if (!expandBlockElem) {
        console.error("Could not find element with ID:", expandBlockID);
        return;
    }
    klmsToggleBlockFullScreen(expandBlockElem, true);
}

function klmsOnBlockExitFullScreen(expandBlockID) {

    const expandBlockElem = document.getElementById(expandBlockID);
    if (!expandBlockElem) {
        console.error("Could not find element with ID:", expandBlockID);
        return;
    }
    klmsToggleBlockFullScreen(expandBlockElem, false);
}

export {klmsOnBlockToFullScreen, klmsOnBlockExitFullScreen};
