/**
 * Module attribute template modal.
 *
 * Defines responsibilities and integration points for components product types.
 */

// Frontend/app/src/components/product_types/AttributeTemplateModal.jsx

import React, { useState, useEffect } from 'react';
import { showErrorToast } from '../../utils/notifications';
import '../common/Modal.css';

// Estilos para o Modal. Podem ser movidos para um arquivo CSS.


function AttributeTemplateModal(


  { isOpen, onClose, attribute, onSave, isSubmitting }) {
    const [formData, setFormData] = useState(DEFAULT_FORM_DATA);
    const isEditing = attribute && attribute.id;

    // Popula o formulÃ¡rio quando o modal abre ou o atributo a ser editado muda
    useEffect(() => {
      if (isOpen) {
        setFormData({
          ...DEFAULT_FORM_DATA,
          label: attribute?.label || DEFAULT_FORM_DATA.label,
          attribute_key: attribute?.attribute_key || DEFAULT_FORM_DATA.attribute_key,
          field_type: attribute?.field_type || DEFAULT_FORM_DATA.field_type,
          description: attribute?.description || DEFAULT_FORM_DATA.description,
          // Garante que 'options' seja uma string formatada corretamente para o textarea
          options: Array.isArray(attribute?.options) ?
          JSON.stringify(attribute.options, null, 2) :
          attribute?.options || DEFAULT_FORM_DATA.options,
          is_required: Boolean(attribute?.is_required),
          default_value: attribute?.default_value || DEFAULT_FORM_DATA.default_value,
          tooltip_text: attribute?.tooltip_text || DEFAULT_FORM_DATA.tooltip_text,
          display_order: attribute?.display_order || DEFAULT_FORM_DATA.display_order
        });
      }
    }, [attribute, isOpen]);

    const handleChange = (e) => {
      const { name, value, type, checked } = e.target;
      setFormData((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
    };

    const handleSubmit = (e) => {
      e.preventDefault();
      if (!formData.label.trim() || !formData.attribute_key.trim()) {
        showErrorToast("RÃ³tulo e Chave do Atributo sÃ£o obrigatÃ³rios.");
        return;
      }

      const payload = { ...formData };

      // Converte o tipo de campo para minÃºsculas, conforme esperado pelo backend
      payload.field_type = String(payload.field_type || '').toLowerCase();

      // Valida e formata o campo 'options' se for um tipo de seleÃ§Ã£o
      if (payload.field_type === 'select' || payload.field_type === 'multiselect') {
        try {
          // Tenta parsear para garantir que Ã© um JSON Array vÃ¡lido
          const parsedOptions = JSON.parse(payload.options);
          if (!Array.isArray(parsedOptions)) {
            showErrorToast("O campo 'OpÃ§Ãµes' deve ser um array JSON vÃ¡lido (ex: [\"OpÃ§Ã£o 1\", \"OpÃ§Ã£o 2\"]).");
            return;
          }
          // O backend espera uma string JSON, entÃ£o mantemos como estÃ¡ no payload
        } catch {
          showErrorToast("O formato das opÃ§Ãµes Ã© invÃ¡lido. Deve ser um array JSON. Ex: [\"Valor1\", \"Valor2\"]");
          return;
        }
      } else {
        payload.options = null; // Garante que opÃ§Ãµes nÃ£o sejam enviadas para outros tipos de campo
      }

      onSave(payload);
    };

    if (!isOpen) return null;

    return (
      <div className="modal-overlay" style={styles.modalOverlay}>
      <div className="modal-content" style={styles.modalContent}>
        <div style={styles.modalHeader} className="modal-header">
          <h3 style={styles.modalTitle}>{isEditing ? 'Editar Atributo' : 'Novo Atributo'}</h3>
          <button
              type="button"
              aria-label="Fechar"
              onClick={onClose}
              className="modal-close-button"
              style={styles.closeButton}
              disabled={isSubmitting}>
              
            &times;
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div style={styles.formGroup}>
            <label htmlFor="label" style={styles.label}>RÃ³tulo (Ex: Cor, MemÃ³ria RAM)*</label>
            <input id="label" name="label" value={formData.label} onChange={handleChange} style={styles.input} required disabled={isSubmitting} />
          </div>
          <div style={styles.formGroup}>
            <label htmlFor="attribute_key" style={styles.label}>Chave do Atributo (Ex: cor, memoria_ram)*</label>
            <input id="attribute_key" name="attribute_key" value={formData.attribute_key} onChange={handleChange} style={styles.input} required disabled={isEditing || isSubmitting} />
            {isEditing && <small>A chave nÃ£o pode ser alterada apÃ³s a criaÃ§Ã£o.</small>}
          </div>
          <div style={styles.formGroup}>
            <label htmlFor="field_type" style={styles.label}>Tipo do Campo</label>
            <select id="field_type" name="field_type" value={formData.field_type} onChange={handleChange} style={styles.input} disabled={isSubmitting}>
                <option value="TEXT">Texto</option>
                <option value="TEXTAREA">Texto Longo</option>
                <option value="NUMBER">NÃºmero</option>
                <option value="BOOLEAN">Sim/NÃ£o</option>
                <option value="SELECT">SeleÃ§Ã£o Ãšnica</option>
                <option value="MULTISELECT">SeleÃ§Ã£o MÃºltipla</option>
                <option value="DATE">Data</option>
            </select>
          </div>
          {(formData.field_type === 'SELECT' || formData.field_type === 'MULTISELECT') &&
            <div style={styles.formGroup}>
                <label htmlFor="options" style={styles.label}>OpÃ§Ãµes (em formato JSON Array)</label>
                <textarea id="options" name="options" value={formData.options} onChange={handleChange} style={styles.textarea} placeholder='Ex: ["P", "M", "G"]' disabled={isSubmitting} />
            </div>
            }
          <div style={styles.formGroup}>
            <label htmlFor="tooltip_text" style={styles.label}>Texto de Ajuda (Tooltip)</label>
            <input id="tooltip_text" name="tooltip_text" value={formData.tooltip_text} onChange={handleChange} style={styles.input} disabled={isSubmitting} />
          </div>
          <div style={styles.formGroup}>
            <label style={styles.checkboxLabel}>
              <input type="checkbox" name="is_required" checked={formData.is_required} onChange={handleChange} style={styles.checkboxInput} disabled={isSubmitting} />
              Ã‰ um campo obrigatÃ³rio?
            </label>
          </div>
          <div style={styles.actions}>
            <button type="button" onClick={onClose} className="btn-secondary" disabled={isSubmitting}>Cancelar</button>
            <button type="submit" className="btn-success" disabled={isSubmitting}>{isSubmitting ? 'Salvando...' : 'Salvar Atributo'}</button>
          </div>
        </form>
      </div>
    </div>);

  }
const styles = { modalOverlay: { position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1100 }, modalContent: { background: 'white', padding: '2rem', borderRadius: 'var(--radius)', width: '90%', maxWidth: '600px', boxShadow: 'var(--shadow-md)' }, modalHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '1px solid var(--border-color)' }, modalTitle: { margin: 0, fontSize: '1.4rem' }, closeButton: { background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#888', lineHeight: 1 }, formGroup: { marginBottom: '1rem' }, label: { display: 'block', marginBottom: '0.5rem', fontWeight: '500' }, input: { width: '100%', padding: '0.7rem', border: '1px solid #ccc', borderRadius: 'var(--radius)', fontSize: '1rem', boxSizing: 'border-box' }, textarea: { width: '100%', padding: '0.7rem', border: '1px solid #ccc', borderRadius: 'var(--radius)', fontSize: '1rem', boxSizing: 'border-box', minHeight: '80px' }, actions: { marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }, checkboxLabel: { display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 'normal' }, checkboxInput: { width: 'auto' } };const DEFAULT_FORM_DATA = { label: '', attribute_key: '', field_type: 'TEXT', description: '', options: '', is_required: false, default_value: '', tooltip_text: '', display_order: 0 };export default AttributeTemplateModal;
