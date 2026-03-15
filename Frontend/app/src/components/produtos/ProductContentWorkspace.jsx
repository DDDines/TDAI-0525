import React from 'react';
import './ProductContentWorkspace.css';

function ProductContentWorkspace({
  titles = [],
  description = '',
  editable = false,
  onTitleChange,
  onDescriptionChange,
  onGenerateTitles,
  onGenerateDescription,
  isGenerating = false,
  disableActions = false,
  showUseAiToggle = false,
  useAi = false,
  onUseAiChange,
  onOpenDedicatedView,
  titleButtonLabel = 'Gerar títulos',
  descriptionButtonLabel = 'Gerar descrição',
  titleHeading = '5 Titulos Sugeridos',
  descriptionHeading = 'Descricao Completa',
  maxTitles = 5,
  emptyTitleMessage = 'Titulo ainda nao gerado para esta posicao.',
  emptyDescriptionMessage = 'Descricao ainda nao gerada.',
}) {
  const visibleTitles = Array.from({ length: maxTitles }).map((_, index) => String(titles[index] || ''));

  return (
    <div className="product-content-workspace">
      <div className="product-content-workspace-toolbar">
        <div className="product-content-workspace-actions">
          {typeof onGenerateTitles === 'function' ? (
            <button
              type="button"
              className="btn-secondary"
              onClick={onGenerateTitles}
              disabled={disableActions || isGenerating}
            >
              {titleButtonLabel}
            </button>
          ) : null}
          {typeof onGenerateDescription === 'function' ? (
            <button
              type="button"
              className="btn-secondary"
              onClick={onGenerateDescription}
              disabled={disableActions || isGenerating}
            >
              {descriptionButtonLabel}
            </button>
          ) : null}
          {typeof onOpenDedicatedView === 'function' ? (
            <button
              type="button"
              className="btn-primary"
              onClick={onOpenDedicatedView}
              disabled={disableActions}
            >
              Abrir tela dedicada
            </button>
          ) : null}
        </div>
        {showUseAiToggle ? (
          <label className="product-content-workspace-toggle">
            <input
              type="checkbox"
              checked={Boolean(useAi)}
              onChange={(event) => onUseAiChange?.(event.target.checked)}
              disabled={disableActions}
            />
            <span>Usar IA</span>
          </label>
        ) : null}
      </div>

      <div className="product-content-workspace-grid">
        <section className="product-content-block">
          <h3>{titleHeading}</h3>
          <div className="product-content-title-list produto-conteudo-title-list">
            {visibleTitles.map((title, index) => (
                  <article
                    key={`workspace-title-${index}`}
                    className="product-content-title-card produto-conteudo-title-card"
                  >
                    <span className="product-content-title-index produto-conteudo-title-index">
                      {index + 1}
                    </span>
                {editable ? (
                  <textarea
                    className="product-content-title-input"
                    rows={2}
                    value={title}
                    onChange={(event) => onTitleChange?.(index, event.target.value)}
                    placeholder={emptyTitleMessage}
                  />
                ) : (
                  <p>{title || emptyTitleMessage}</p>
                )}
              </article>
            ))}
          </div>
        </section>

        <section className="product-content-block">
          <h3>{descriptionHeading}</h3>
          {editable ? (
            <textarea
              className="product-content-description-input produto-conteudo-description"
              rows={18}
              value={String(description || '')}
              onChange={(event) => onDescriptionChange?.(event.target.value)}
              placeholder={emptyDescriptionMessage}
            />
          ) : (
            <div className="product-content-description produto-conteudo-description">
              {description || emptyDescriptionMessage}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default ProductContentWorkspace;
