/******/ (function() { // webpackBootstrap
/*!*****************************************!*\
  !*** ./kinesinlms/static/src/course.js ***!
  \*****************************************/
// course.js
// This file holds javascript that should be run on any "course" page.

function klmsOnToggleTopNav(hideNavBar) {
  console.log("klmsOnToggleTopNav");
  const btnShowTopNav = document.getElementById('btnShowTopNav');
  const topNav = document.getElementById('site-top-nav');
  if (hideNavBar) {
    if (topNav) {
      topNav.style.display = "none";
    }
    if (btnShowTopNav) {
      btnShowTopNav.style.display = "flex";
    }
  } else {
    if (topNav) {
      topNav.style.display = "flex";
      topNav.classList.remove("d-none");
    }
    if (btnShowTopNav) {
      btnShowTopNav.style.display = "none";
    }
  }
  const myTooltipEl = document.getElementById('btnShowTopNav');
  let tooltip = bootstrap.Tooltip.getInstance(myTooltipEl);
  setTimeout(function () {
    tooltip.hide();
  }, 5);
}
function klmsSaveSetting(hideNavBar) {
  try {
    const targetURL = `/courses/toggle_main_nav/`;
    const payload = {
      'hide_main_nav': hideNavBar
    };
    axios.request({
      url: targetURL,
      method: 'post',
      withCredentials: true,
      data: payload
    }).catch(error => {
      console.log("response: ", error);
    });
  } catch (error) {
    console.log("Error saving show/hide top nav setting:", error);
  }
}

/*
    Try to auto-scroll to the 'here' marker in the left nav the first
    time it's shown on a page.
    Only do this once as the user probably expects the nav to be
    scrolled to the last point they left it if they close and then
    reopen the nav.
 */
let klmsFirstNavClick = true;
function klmsOnLeftNavToggle(event) {
  setTimeout(function () {
    //your code to be executed after 1 second
  }, 100);
  console.log("klmsOnLeftNavToggle", event);
  if (klmsFirstNavClick) {
    try {
      const sidebarElem = document.getElementById('sidebar');
      const youAreHereMarkerElem = document.getElementById("you-are-here-marker");
      if (sidebarElem && youAreHereMarkerElem) {
        youAreHereMarkerElem.scrollIntoView({
          block: "center"
        });
        klmsFirstNavClick = false;
      }
    } catch (e) {
      console.error("Could not scroll course nav current unit node into view.");
    }
  }
}
window.klmsOnToggleTopNav = klmsOnToggleTopNav;
window.klmsSaveSetting = klmsSaveSetting;
window.addEventListener('DOMContentLoaded', event => {
  // Set up a listener for left nav toggle button.
  const sidebarCollapseBtn = document.getElementById("sidebarCollapse");
  if (sidebarCollapseBtn) {
    sidebarCollapseBtn.addEventListener('click', klmsOnLeftNavToggle);
  }

  // Set up show/hide top nav buttons.
  const btnShowTopNav = document.getElementById('btnShowTopNav');
  if (btnShowTopNav) {
    btnShowTopNav.addEventListener('click', () => {
      klmsOnToggleTopNav(false);
      klmsSaveSetting(false);
    });
  }
  const btnHideTopNav = document.getElementById('btnHideTopNav');
  if (btnHideTopNav) {
    btnHideTopNav.addEventListener('click', () => {
      klmsOnToggleTopNav(true);
      klmsSaveSetting(true);
    });
  }
});
/******/ })()
;
//# sourceMappingURL=kinesinlms-course.bundle.js.map