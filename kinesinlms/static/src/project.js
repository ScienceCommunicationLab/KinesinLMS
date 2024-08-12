// project.js
// This file holds JS used across the KinesinLMS site. It's responsible
// for running functions that should be called on any page view (e.g. tooltips, toasts, etc)

// All libraries that should be available everywhere through the window object,
// but are still installed via npm.


// Import all javascript libraries and functions.
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import * as bootstrap from 'bootstrap'
// Import fullscreen toggle functions
import { klmsOnBlockExitFullScreen, klmsOnBlockToFullScreen } from './unit.js';
import 'htmx.org';
import Alpine from 'alpinejs';


// Libraries that should be available everywhere through the window object,
// but are still installed via npm. Most of these libraries are used in Webpack
// code as well, so including them here will make the client download them only once.


window.React = require('react');
window.ReactDOM = require('react-dom');
window.axios = require('axios');
window.bootstrap = require('bootstrap');

window.htmx = require('htmx.org');

window.Alpine = Alpine;


window.addEventListener('DOMContentLoaded', (event) => {

    console.log("DOM fully loaded and parsed....");

    // Bootstrap setup...
    klmsEnableToasts();
    klmsEnableTooltips();

    // Start Alpine. See https://github.com/alpinejs/alpine/discussions/2274
    window.Alpine.start();

});

// Javascript that should run on page load on any page.
function klmsEnableToasts() {
    try {
        console.log("Enabling bootstrap toasts...")
        let toastElList = [].slice.call(document.querySelectorAll('.toast'))
        let toastList = toastElList
            .filter(function (toastEl) {
                return toastEl.id !== 'htmx-cohort-student-toast';
            })
            .map(function (toastEl) {
                return new bootstrap.Toast(toastEl, {});
            }
            )
        toastList.forEach(toast => toast.show());
    } catch (err) {
        console.log("Error initializing toasts: ", err)
    }
}

function klmsEnableTooltips() {
    try {
        console.log("Enabling bootstrap tooltips...")
        let tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
        let tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl)
        })
    } catch (err) {
        console.log("Error initializing tooltips: ", err)
    }
}

function klmsOnUnitMarkerDoubleClick(unitURL) {
    window.location.href = unitURL;
}

//Export to window level
window.klmsOnBlockToFullScreen = klmsOnBlockToFullScreen
window.klmsOnBlockExitFullScreen = klmsOnBlockExitFullScreen
window.klmsEnableTooltips = klmsEnableTooltips
window.klmsEnableToasts = klmsEnableToasts
window.klmsOnUnitMarkerDoubleClick = klmsOnUnitMarkerDoubleClick


