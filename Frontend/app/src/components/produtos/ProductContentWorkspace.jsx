/**
 * Module product content workspace.
 *
 * Defines responsibilities and integration points for components produtos.
 */

import React from 'react';
import './ProductContentWorkspace.css';

function ProductContentWorkspace({
  titles = [],
  description = '',
  editable = false,
  onTitleChange,
  onDescriptionChange,
  titleHeading = '5 títulos sugeridos',
  descriptionHeading = 'Descrição completa',
  maxTitles = 5,
  emptyTitleMessage = 'Título ainda não gerado para esta posição.',
  emptyDescriptionMessage = 'Descrição ainda não gerada.',
}) {
  const visibleTitles = Array.from({ length: maxTitles }).map((_, index) => String(titles[index] || ''));

  return (
    <div className="product-content-workspace">
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
