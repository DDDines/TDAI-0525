// Frontend/app/src/components/product_types/AttributeTemplateModal.jsx

import React, { useState, useEffect } from 'react';
import { showErrorToast } from '../../utils/notifications';

// Estilos para o Modal. Podem ser movidos para um arquivo CSS.
const styles = {
    modalOverlay: { position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1100 },
    modalContent: { background: 'white', padding: '2rem', borderRadius: 'var(--radius)', width: '90%', maxWidth: '600px', boxShadow: 'var(--shadow-md)' },
    modalHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '1px solid var(--border-color)'},
    modalTitle: { margin: 0, fontSize: '1.4rem' },
    closeButton: { background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer'},
    formGroup: { marginBottom: '1rem' },
    label: { display: 'block', marginBottom: '0.5rem', fontWeight: '500' },
    input: { width: '100%', padding: '0.7rem', border: '1px solid #ccc', borderRadius: 'var(--radius)', fontSize: '1rem', boxSizing: 'border-box' },
    textarea: { width: '100%', padding: '0.7rem', border: '1px solid #ccc', borderRadius: 'var(--radius)', fontSize: '1rem', boxSizing: 'border-box', minHeight: '80px' },
    actions: { marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' },
    checkboxLabel: { display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 'normal'},
    checkboxInput: { width: 'auto' }
};


const AttributeTemplateModal = ({ isOpen, onClose, attribute, onSave, isSubmitting }) => {
  const [formData, setFormData] = useState({});
  const isEditing = attribute && attribute.id;

  // Popula o formulário quando o modal abre ou o atributo a ser editado muda
  useEffect(() => {
    if (isOpen) {
      setFormData({
        label: attribute?.label || '',
        attribute_key: attribute?.attribute_key || '',
        field_type: attribute?.field_type || 'TEXT',
        description: attribute?.description || '',
        // Garante que 'options' seja uma string formatada corretamente para o textarea
        options: Array.isArray(attribute?.options) ? JSON.stringify(attribute.options, null, 2) : (attribute?.options || ''),
        is_required: attribute?.is_required || false,
        default_value: attribute?.default_value || '',
        tooltip_text: attribute?.tooltip_text || '',
        display_order: attribute?.display_order || 0,
      });
    }
  }, [attribute, isOpen]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.label.trim() || !formData.attribute_key.trim()) {
      showErrorToast("Rótulo e Chave do Atributo são obrigatórios.");
      return;
    }

    const payload = { ...formData };

    // Valida e formata o campo 'options' se for um tipo de seleção
    if (payload.field_type === 'SELECT' || payload.field_type === 'MULTISELECT') {
      try {
        // Tenta parsear para garantir que é um JSON Array válido
        const parsedOptions = JSON.parse(payload.options);
        if (!Array.isArray(parsedOptions)) {
            showErrorToast("O campo 'Opções' deve ser um array JSON válido (ex: [\"Opção 1\", \"Opção 2\"]).");
            return;
        }
        // O backend espera uma string JSON, então mantemos como está no payload
      } catch (error) {
        showErrorToast("O formato das opções é inválido. Deve ser um array JSON. Ex: [\"Valor1\", \"Valor2\"]");
        return;
      }
    } else {
      payload.options = null; // Garante que opções não sejam enviadas para outros tipos de campo
    }

    onSave(payload);
  };

  if (!isOpen) return null;

  return (
    <div style={styles.modalOverlay}>
      <div style={styles.modalContent}>
        <div style={styles.modalHeader}>
          <h3 style={styles.modalTitle}>{isEditing ? 'Editar Atributo' : 'Novo Atributo'}</h3>
          <button onClick={onClose} style={styles.closeButton} disabled={isSubmitting}>&times;</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div style={styles.formGroup}>
            <label htmlFor="label" style={styles.label}>Rótulo (Ex: Cor, Memória RAM)*</label>
            <input id="label" name="label" value={formData.label} onChange={handleChange} style={styles.input} required disabled={isSubmitting} />
          </div>
          <div style={styles.formGroup}>
            <label htmlFor="attribute_key" style={styles.label}>Chave do Atributo (Ex: cor, memoria_ram)*</label>
            <input id="attribute_key" name="attribute_key" value={formData.attribute_key} onChange={handleChange} style={styles.input} required disabled={isEditing || isSubmitting} />
            {isEditing && <small>A chave não pode ser alterada após a criação.</small>}
          </div>
          <div style={styles.formGroup}>
            <label htmlFor="field_type" style={styles.label}>Tipo do Campo</label>
            <select id="field_type" name="field_type" value={formData.field_type} onChange={handleChange} style={styles.input} disabled={isSubmitting}>
                <option value="TEXT">Texto</option>
                <option value="TEXTAREA">Texto Longo</option>
                <option value="NUMBER">Número</option>
                <option value="BOOLEAN">Sim/Não</option>
                <option value="SELECT">Seleção Única</option>
                <option value="MULTISELECT">Seleção Múltipla</option>
                <option value="DATE">Data</option>
            </select>
          </div>
          {(formData.field_type === 'SELECT' || formData.field_type === 'MULTISELECT') && (
            <div style={styles.formGroup}>
                <label htmlFor="options" style={styles.label}>Opções (em formato JSON Array)</label>
                <textarea id="options" name="options" value={formData.options} onChange={handleChange} style={styles.textarea} placeholder='Ex: ["P", "M", "G"]' disabled={isSubmitting} />
            </div>
          )}
          <div style={styles.formGroup}>
            <label htmlFor="tooltip_text" style={styles.label}>Texto de Ajuda (Tooltip)</label>
            <input id="tooltip_text" name="tooltip_text" value={formData.tooltip_text} onChange={handleChange} style={styles.input} disabled={isSubmitting} />
          </div>
          <div style={styles.formGroup}>
            <label style={styles.checkboxLabel}>
              <input type="checkbox" name="is_required" checked={formData.is_required} onChange={handleChange} style={styles.checkboxInput} disabled={isSubmitting} />
              É um campo obrigatório?
            </label>
          </div>
          <div style={styles.actions}>
            <button type="button" onClick={onClose} className="btn-secondary" disabled={isSubmitting}>Cancelar</button>
            <button type="submit" className="btn-success" disabled={isSubmitting}>{isSubmitting ? 'Salvando...' : 'Salvar Atributo'}</button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AttributeTemplateModal;