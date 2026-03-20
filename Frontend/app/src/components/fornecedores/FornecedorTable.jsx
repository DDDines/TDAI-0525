/**
 * Module fornecedor table.
 *
 * Defines responsibilities and integration points for components fornecedores.
 */

import React, { useEffect, useRef, useState } from 'react';
import {
  LuBuilding2,
  LuCalendarDays,
  LuCircleSlash,
  LuExternalLink,
  LuGlobe,
  LuListChecks,
} from 'react-icons/lu';
import './FornecedorTable.css';

function buildSiteData(rawValue) {
  const raw = String(rawValue || '').trim();
  if (!raw) {
    return null;
  }

  const href = /^https?:\/\//i.test(raw) ? raw : `https://${raw}`;

  try {
    const parsed = new URL(href);
    const hostname = parsed.hostname.replace(/^www\./i, '') || raw;
    const pathLabel =
      parsed.pathname && parsed.pathname !== '/'
        ? `${hostname}${parsed.pathname}`
        : parsed.search
          ? `${hostname}${parsed.search}`
          : '';
    return {
      href,
      hostname,
      label: pathLabel,
    };
  } catch {
    return {
      href,
      hostname: raw.replace(/^https?:\/\//i, '').replace(/^www\./i, ''),
      label: '',
    };
  }
}

function formatCreatedAt(value) {
  if (!value) {
    return '--';
  }

  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return '--';
  }

  return new Intl.DateTimeFormat('pt-BR').format(parsedDate);
}

function buildInitials(name) {
  const safeName = String(name || '').trim();
  if (!safeName) {
    return 'F';
  }

  return safeName
    .split(/\s+/)
    .slice(0, 2)
    .map((chunk) => chunk.charAt(0).toUpperCase())
    .join('');
}

function FornecedorAvatar({ fornecedor }) {
  const [showImage, setShowImage] = useState(Boolean(fornecedor?.logo_url));

  if (showImage && fornecedor?.logo_url) {
    return (
      <span className="fornecedor-avatar fornecedor-avatar-image-wrap">
        <img
          src={fornecedor.logo_url}
          alt={`Logo de ${fornecedor.nome}`}
          className="fornecedor-avatar-image"
          onError={() => setShowImage(false)}
        />
      </span>
    );
  }

  return <span className="fornecedor-avatar">{buildInitials(fornecedor?.nome)}</span>;
}

function FornecedorTable({
  fornecedores,
  onRowClick,
  onSelectRow,
  selectedIds,
  onSelectAllRows,
  selectionMenuItems = [],
  isLoading,
}) {
  const safeFornecedores = Array.isArray(fornecedores) ? fornecedores : [];
  const selectedList = Array.isArray(selectedIds) ? selectedIds : [];
  const pageSelected =
    safeFornecedores.length > 0 && selectedList.length === safeFornecedores.length;
  const hasSelectionMenu = Array.isArray(selectionMenuItems) && selectionMenuItems.length > 0;
  const [isSelectionMenuOpen, setIsSelectionMenuOpen] = useState(false);
  const selectionMenuRef = useRef(null);

  useEffect(() => {
    if (!isSelectionMenuOpen) {
      return undefined;
    }

    const handleOutsideClick = (event) => {
      if (!selectionMenuRef.current?.contains(event.target)) {
        setIsSelectionMenuOpen(false);
      }
    };

    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        setIsSelectionMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleOutsideClick);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isSelectionMenuOpen]);

  return (
    <table className="fornecedor-table" id="forn-table">
      <thead>
        <tr>
          <th className="select fornecedor-select-header">
            {hasSelectionMenu ? (
              <div className="fornecedor-selection-menu" ref={selectionMenuRef}>
                <button
                  type="button"
                  className={`fornecedor-selection-menu-trigger${isSelectionMenuOpen ? ' is-active' : ''}`}
                  aria-label="Opcoes de selecao"
                  aria-haspopup="menu"
                  aria-expanded={isSelectionMenuOpen}
                  onClick={() => setIsSelectionMenuOpen((currentValue) => !currentValue)}
                  disabled={safeFornecedores.length === 0 && selectedList.length === 0}
                >
                  <LuListChecks />
                </button>
                {isSelectionMenuOpen ? (
                  <div className="fornecedor-selection-menu-dropdown" role="menu">
                    {selectionMenuItems.map((item) => (
                      <button
                        key={item.key}
                        type="button"
                        role="menuitem"
                        className={`fornecedor-selection-menu-item${item.variant === 'danger' ? ' is-danger' : ''}`}
                        onClick={() => {
                          item.onClick?.();
                          setIsSelectionMenuOpen(false);
                        }}
                        disabled={item.disabled}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="fornecedor-selection-header">
                <label className="fornecedor-selection-toggle" title="Selecionar pagina atual">
                  <input
                    type="checkbox"
                    id="select-all-forn"
                    aria-label="Selecionar pagina atual"
                    onChange={(event) => onSelectAllRows(event.target.checked)}
                    checked={pageSelected}
                    disabled={safeFornecedores.length === 0}
                  />
                </label>
              </div>
            )}
          </th>
          <th>Fornecedor</th>
          <th>Site</th>
          <th>Cadastro</th>
        </tr>
      </thead>
      <tbody>
        {safeFornecedores.length > 0 ? (
          safeFornecedores.map((fornecedor) => {
            const siteData = buildSiteData(fornecedor.site_url);
            const isSelected = selectedList.includes(fornecedor.id);

            return (
              <tr
                key={fornecedor.id}
                onClick={() => onRowClick(fornecedor)}
                className={`clickable-row${isSelected ? ' is-selected' : ''}`}
              >
                <td className="select" onClick={(event) => event.stopPropagation()}>
                  <input
                    type="checkbox"
                    className="row-select-forn"
                    checked={isSelected}
                    onChange={() => onSelectRow(fornecedor.id)}
                    onClick={(event) => event.stopPropagation()}
                  />
                </td>
                <td className="name-cell">
                  <div className="fornecedor-identity">
                    <FornecedorAvatar fornecedor={fornecedor} />
                    <div className="fornecedor-identity-copy">
                      <strong>{fornecedor.nome}</strong>
                      <span>
                        <LuBuilding2 />
                        ID {fornecedor.id}
                      </span>
                    </div>
                  </div>
                </td>
                <td className="site-cell">
                  {siteData ? (
                    <a
                      href={siteData.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(event) => event.stopPropagation()}
                      className="fornecedor-site-link"
                    >
                      <div className="fornecedor-site-copy">
                      <strong>
                        <LuGlobe />
                        {siteData.hostname}
                      </strong>
                      {siteData.label ? <span>{siteData.label}</span> : null}
                    </div>
                      <LuExternalLink className="fornecedor-site-external" />
                    </a>
                  ) : (
                    <span className="fornecedor-site-empty">
                      <LuCircleSlash />
                      Sem site cadastrado
                    </span>
                  )}
                </td>
                <td className="date-cell">
                  <div className="fornecedor-date-stack">
                    <strong>{formatCreatedAt(fornecedor.created_at)}</strong>
                    <span>
                      <LuCalendarDays />
                      Cadastro
                    </span>
                  </div>
                </td>
              </tr>
            );
          })
        ) : (
          <tr>
            <td colSpan="4" className="fornecedor-empty-cell">
              {isLoading ? 'Carregando fornecedores...' : 'Nenhum fornecedor encontrado.'}
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}

export default FornecedorTable;
