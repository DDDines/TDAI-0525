// Frontend/app/src/components/produtos/shared/AttributeField.jsx
import React from 'react';

// Estilos (podem vir de um arquivo CSS compartilhado ou serem definidos aqui/inline)
const fieldStyles = {
  formGroup: { marginBottom: '1rem' },
  label: { display: 'block', marginBottom: '0.3rem', fontWeight: '500', color: '#333', fontSize: '0.9rem' },
  input: { width: '100%', padding: '0.6rem 0.75rem', border: '1px solid #d1d5db', borderRadius: 'var(--radius)', fontSize: '0.95rem', boxSizing: 'border-box' },
  select: { width: '100%', padding: '0.6rem 0.75rem', border: '1px solid #d1d5db', borderRadius: 'var(--radius)', fontSize: '0.95rem', boxSizing: 'border-box', backgroundColor: 'white' },
  textarea: { width: '100%', minHeight: '80px', padding: '0.6rem 0.75rem', border: '1px solid #d1d5db', borderRadius: 'var(--radius)', fontSize: '0.95rem', boxSizing: 'border-box', resize: 'vertical' },
  checkboxContainer: { display: 'flex', alignItems: 'center', marginTop: '0.25rem'},
  checkbox: { marginRight: '0.5rem', width: 'auto', height: 'auto', cursor: 'pointer' },
  checkboxLabel: { fontWeight: 'normal', fontSize: '0.95rem', cursor: 'pointer', userSelect: 'none' },
  tooltipIcon: { cursor: 'help', marginLeft: '4px', color: '#6b7280', fontSize: '0.8em' }
};

function AttributeField({ attributeTemplate, value, onChange, disabled = false }) {
  const {
    attribute_key,
    label,
    field_type,
    options: optionsString,
    is_required,
    tooltip_text,
    default_value // default_value vem do template
  } = attributeTemplate;

  const fieldId = `attr-${attribute_key}`;

  // Determinar o valor inicial/atual do campo
  // Se 'value' (do estado dynamicAttributes) for undefined, usar default_value do template.
  // Se ambos forem undefined, usar um valor padrão apropriado para o tipo de campo.
  let currentValue;
  if (value !== undefined && value !== null) {
    currentValue = value;
  } else if (default_value !== undefined && default_value !== null) {
    currentValue = field_type === 'boolean'
      ? (String(default_value).toLowerCase() === 'true' || default_value === '1')
      : default_value;
  } else {
    currentValue = field_type === 'boolean' ? false : '';
  }


  const handleChange = (e) => {
    const eventValue = field_type === 'boolean' ? e.target.checked : e.target.value;
    onChange(attribute_key, eventValue);
  };

  let parsedOptions = [];
  if ((field_type === 'select' || field_type === 'multiselect') && optionsString) {
    try {
      parsedOptions = JSON.parse(optionsString);
      if (parsedOptions.length > 0 && typeof parsedOptions[0] === 'string') {
        parsedOptions = parsedOptions.map(opt => ({ value: opt, label: opt }));
      }
    } catch (error) {
      console.error(`Erro ao parsear opções JSON para o atributo "${label}":`, optionsString, error);
      parsedOptions = [];
    }
  }


  return (
    <div style={fieldStyles.formGroup}>
      <label htmlFor={fieldId} style={fieldStyles.label}>
        {label}{is_required ? <span style={{color: 'var(--danger)'}}>*</span> : ''}
        {tooltip_text && <span title={tooltip_text} style={fieldStyles.tooltipIcon}>ⓘ</span>}
      </label>

      {field_type === 'text' && (
        <input
          type="text"
          id={fieldId}
          value={String(currentValue)} // Garantir que seja string
          onChange={handleChange}
          style={fieldStyles.input}
          placeholder={field_type === 'text' && default_value ? String(default_value) : `Digite ${label.toLowerCase()}`}
          disabled={disabled}
          required={is_required}
        />
      )}
      {field_type === 'textarea' && (
        <textarea
          id={fieldId}
          value={String(currentValue)} // Garantir que seja string
          onChange={handleChange}
          style={fieldStyles.textarea}
          placeholder={field_type === 'textarea' && default_value ? String(default_value) : `Digite ${label.toLowerCase()}`}
          disabled={disabled}
          required={is_required}
        />
      )}
      {field_type === 'number' && (
        <input
          type="number"
          id={fieldId}
          value={String(currentValue)} // Garantir que seja string, o browser converte
          onChange={handleChange}
          style={fieldStyles.input}
          placeholder={field_type === 'number' && default_value ? String(default_value) : `Digite ${label.toLowerCase()}`}
          disabled={disabled}
          required={is_required}
        />
      )}
      {field_type === 'boolean' && (
        <div style={fieldStyles.checkboxContainer}>
          <input
            type="checkbox"
            id={fieldId}
            checked={Boolean(currentValue)} // Converte para booleano
            onChange={handleChange}
            disabled={disabled}
            style={fieldStyles.checkbox}
          />
          <label htmlFor={fieldId} style={fieldStyles.checkboxLabel}>
            {/* O label principal já está acima, este é para clicar no texto ao lado do checkbox */}
            {label}
          </label>
        </div>
      )}
      {field_type === 'select' && (
        <select
          id={fieldId}
          value={String(currentValue)} // Garantir que seja string para correspondência de <option value>
          onChange={handleChange}
          style={fieldStyles.select}
          disabled={disabled}
          required={is_required}
        >
          <option value="">-- Selecione {label.toLowerCase()} --</option>
          {parsedOptions.map((opt, index) => (
            <option key={opt.value || index} value={String(opt.value)}>
              {opt.label || opt.value}
            </option>
          ))}
        </select>
      )}
      {field_type === 'date' && (
        <input
          type="date"
          id={fieldId}
          value={String(currentValue)} // O valor para input date deve ser YYYY-MM-DD
          onChange={handleChange}
          style={fieldStyles.input}
          disabled={disabled}
          required={is_required}
        />
      )}
      {/* Adicionar suporte para 'multiselect' aqui no futuro */}
      {!['text', 'textarea', 'number', 'boolean', 'select', 'date'].includes(field_type) && (
          <p style={{color: 'var(--danger)', fontSize: '0.8em'}}>Tipo de campo '{field_type}' não suportado por AttributeField.jsx.</p>
      )}
    </div>
  );
}

export default AttributeField;
