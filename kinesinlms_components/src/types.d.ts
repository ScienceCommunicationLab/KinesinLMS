// @ts-ignore
import type Bootstrap from 'bootstrap';

/**
 The interface below gives components access to the
 Bootstrap library and some top-level functions that are
 all defined in the main app.
 */

declare global {
    interface Window {
        bootstrap: typeof Bootstrap;
        klmsOnBlockToFullScreen: Function;
        klmsOnBlockExitFullScreen: Function;
        klmsEnableTooltips: Function;
        klmsEnableToasts: Function;
        klmsOnUnitMarkerDoubleClick: Function;
    }
}
