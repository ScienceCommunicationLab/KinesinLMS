import { useCallback, useEffect, useState } from "react";

declare const window: any;


/**
 * Utility to help you check if Bootstrap is ready to use.
 * Optionally can check for a specific feature (e.g., 'Tooltip') as well.
 * If Bootstrap or the required feature is not enabled after 10 seconds, nothing will happen.
 */
export default function useBootstrapReady(
    bootstrapFeature?: keyof typeof window.bootstrap
): boolean {
    const [isReady, setIsReady] = useState(false);

    const isBootstrapAvailable = useCallback(() => {
        // Bootstrap is not yet available.
        if (!window.bootstrap) {
            return false;
        }

        // Bootstrap feature is not yet available.
        if (bootstrapFeature && !window.bootstrap[bootstrapFeature]) {
            return false;
        }

        // Bootstrap and the feature (if needed) are enabled.
        return true;
    }, []);

    useEffect(() => {
        // Check if Bootstrap is ready every 100ms.
        const intervalId = window.setInterval(() => {
            if (isBootstrapAvailable()) {
                setIsReady(true);
                clearTimeout(timeoutId);
                clearInterval(intervalId);
            }
        }, 100);

        // After 10 seconds, we stop checking and `isReady` stays `false`.
        const timeoutId = window.setTimeout(() => {
            clearInterval(intervalId);
            if (!isBootstrapAvailable()) {
                if (bootstrapFeature) {
                    console.warn(`Could not enable Bootstrap and/or the required feature '${String(bootstrapFeature)}' after 10 seconds...`);
                } else {
                    console.warn(`Could not enable Bootstrap after 10 seconds...`);
                }
            }
        }, 10 * 1000);

        return () => {
            clearTimeout(timeoutId);
            clearInterval(intervalId);
        };
    }, [isBootstrapAvailable]);

    return isReady;
}
