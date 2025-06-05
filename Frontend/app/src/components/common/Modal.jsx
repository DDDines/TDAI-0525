// Frontend/app/src/components/common/Modal.jsx
import React from 'react';
import './Modal.css'; // Opcional: para estilização do modal

const Modal = ({ isOpen, onClose, title, children }) => {
    if (!isOpen) {
        return null;
    }

    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <div className="modal-header">
                    <h2>{title}</h2>
                    <button className="modal-close-button" onClick={onClose}>
                        &times;
                    </button>
                </div>
                <div className="modal-body">
                    {children}
                </div>
            </div>
        </div>
    );
};

export default Modal;