import React, { VFC } from 'react';

interface Props {
    htmlContent: string;
}

const StaticCell: VFC<Props> = ({ htmlContent }) => {
    return (
        <div dangerouslySetInnerHTML={{ __html: htmlContent }}></div>
    );
};

export default StaticCell;
