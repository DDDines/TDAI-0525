import React, { useState, useEffect } from 'react';
import Modal from '../common/Modal';

const EditProductTypeModal = ({ isOpen, onClose, type, onSave, isSubmitting }) => {
  const [friendlyName, setFriendlyName] = useState('');
  const [description, setDescription] = useState('');
  const [keyName, setKeyName] = useState('');

  useEffect(() => {
    if (isOpen && type) {
      setFriendlyName(type.friendly_name || '');
      setDescription(type.description || '');
      setKeyName(type.key_name || '');
    }
  }, [isOpen, type]);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave({ friendly_name: friendlyName, description, key_name: keyName });
  };

  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Editar Tipo de Produto">
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="edit-type-friendly-name">Nome Amigável*</label>
          <input
            id="edit-type-friendly-name"
            type="text"
            value={friendlyName}
            onChange={(e) => setFriendlyName(e.target.value)}
            className="form-control"
            required
            disabled={isSubmitting}
          />
        </div>
        <div className="form-group">
          <label htmlFor="edit-type-key-name">Chave</label>
          <input
            id="edit-type-key-name"
            type="text"
            value={keyName}
            onChange={(e) => setKeyName(e.target.value)}
            className="form-control"
            disabled
          />
          <small>Este valor identifica o tipo e normalmente não deve ser alterado.</small>
        </div>
        <div className="form-group">
          <label htmlFor="edit-type-description">Descrição</label>
          <textarea
            id="edit-type-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="form-control"
            disabled={isSubmitting}
          />
        </div>
        <div className="modal-actions">
          <button type="button" onClick={onClose} className="btn-secondary" disabled={isSubmitting}>Cancelar</button>
          <button type="submit" className="btn-success" disabled={isSubmitting}>{isSubmitting ? 'Salvando...' : 'Salvar'}</button>
        </div>
      </form>
    </Modal>
  );
};

export default EditProductTypeModal;
