import React, { useState, useEffect } from 'react';
import Modal from '../common/Modal';
import { useProductTypes } from '../../contexts/ProductTypeContext';
import { showErrorToast } from '../../utils/notifications';

const NewProductTypeModal = ({ isOpen, onClose, onCreated }) => {
  const { addProductType } = useProductTypes();
  const [friendlyName, setFriendlyName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setFriendlyName('');
      setIsSubmitting(false);
    }
  }, [isOpen]);

  const handleSave = async () => {
    if (!friendlyName.trim()) {
      showErrorToast('O Nome Amigável é obrigatório.');
      return;
    }
    const keyName = friendlyName
      .trim()
      .toLowerCase()
      .replace(/\s+/g, '_')
      .replace(/[^a-z0-9_]/g, '');
    if (!keyName) {
      showErrorToast('Não foi possível gerar uma chave válida a partir do nome.');
      return;
    }

    setIsSubmitting(true);
    try {
      const newType = await addProductType({
        key_name: keyName,
        friendly_name: friendlyName.trim(),
        attribute_templates: [],
      });
      if (onCreated) onCreated(newType);
      onClose();
    } catch (err) {
      // Erros já são tratados no contexto
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Criar Novo Tipo de Produto">
      <div className="form-group">
        <label htmlFor="new-type-friendly-name">Nome Amigável*:</label>
        <input
          type="text"
          id="new-type-friendly-name"
          value={friendlyName}
          onChange={(e) => setFriendlyName(e.target.value)}
          className="form-control"
          placeholder="Ex: Eletrônicos, Vestuário"
          disabled={isSubmitting}
        />
        <small>A "chave" será gerada automaticamente a partir do nome (ex: 'eletronicos').</small>
      </div>
      <div className="modal-actions">
        <button onClick={onClose} className="btn-secondary" disabled={isSubmitting}>
          Cancelar
        </button>
        <button onClick={handleSave} className="btn-success" disabled={isSubmitting}>
          {isSubmitting ? 'Salvando...' : 'Salvar Tipo'}
        </button>
      </div>
    </Modal>
  );
};

export default NewProductTypeModal;
