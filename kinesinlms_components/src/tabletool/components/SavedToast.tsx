import { Toast } from 'react-bootstrap';
import React, { VFC } from 'react';

interface Props {
    isVisible: boolean;
    handleClose: () => void;
}

const SavedToast: VFC<Props> = ({ isVisible, handleClose }) => {
    return (
        <Toast
           className="sit-toast"
           show={isVisible}
           onClick={() => handleClose()}
           onClose={() => handleClose()}
           delay={1750}
           autohide
        >
            <Toast.Body><i className="bi bi-check"></i> Table saved.</Toast.Body>
        </Toast>
    )
};

export default SavedToast;
