import React, { VFC } from 'react';

const SavingNotice: VFC = () => {
    return (
        <div className="sit-saving-notice" data-testid="saving-notice">
            <div className="spinner-border" role="status"></div>
            &nbsp;Saving ...
        </div>
    )
};

export default SavingNotice;
