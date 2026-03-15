/**
 * Module topbar.
 *
 * Defines responsibilities and integration points for components.
 */

import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LuArrowRight, LuMenu, LuSearch } from 'react-icons/lu';
import { useAuth } from '../contexts/AuthContext';
import searchService from '../services/searchService';
import UserMenu from './UserMenu.jsx';
import ThemeToggle from './ThemeToggle.jsx';

const SEARCH_TYPE_LABELS = {
  produto: 'Produto',
  fornecedor: 'Fornecedor',
  product_type: 'Tipo',
  tipo: 'Tipo',
  tipo_de_produto: 'Tipo',
  usuario: 'Usuario',
  user: 'Usuario',
};

const DESKTOP_HOVER_BREAKPOINT = 1024;

function formatSearchTypeLabel(type) {
  const normalized = String(type || '').trim().toLowerCase();
  return SEARCH_TYPE_LABELS[normalized] || type || 'Item';
}

function resolveSearchNavigationRoute(type) {
  const normalizedType = String(type || '').trim().toLowerCase();
  if (normalizedType === 'produto') {
    return '/produtos';
  }
  if (normalizedType === 'fornecedor') {
    return '/fornecedores';
  }
  if (normalizedType === 'product_type' || normalizedType === 'tipo' || normalizedType === 'tipo_de_produto') {
    return '/tipos-de-produto';
  }
  if (normalizedType === 'usuario' || normalizedType === 'user') {
    return '/configuracoes';
  }
  return '/dashboard';
}

function canUseHoverSearch() {
  if (typeof window === 'undefined') {
    return false;
  }
  return window.innerWidth >= DESKTOP_HOVER_BREAKPOINT;
}

function Topbar({ viewTitle, toggleSidebar }) {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchPinned, setSearchPinned] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!searchOpen) {
      setSearchTerm('');
      setSearchResults([]);
      setSearchLoading(false);
      setSearchPinned(false);
      return;
    }

    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, [searchOpen]);

  useEffect(() => {
    if (!searchOpen) {
      return undefined;
    }

    function handleClickOutside(event) {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setSearchOpen(false);
      }
    }

    function handleEscape(event) {
      if (event.key === 'Escape') {
        setSearchOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [searchOpen]);

  useEffect(() => {
    if (!searchOpen) {
      return undefined;
    }

    const trimmed = searchTerm.trim();
    if (!trimmed) {
      setSearchResults([]);
      setSearchLoading(false);
      return undefined;
    }

    let cancelled = false;
    setSearchLoading(true);
    const timer = window.setTimeout(async () => {
      try {
        const data = await searchService.searchAll(trimmed);
        if (!cancelled) {
          setSearchResults(Array.isArray(data?.results) ? data.results : []);
        }
      } catch (err) {
        if (!cancelled) {
          console.error('Erro ao buscar:', err);
          setSearchResults([]);
        }
      } finally {
        if (!cancelled) {
          setSearchLoading(false);
        }
      }
    }, 180);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [searchOpen, searchTerm]);

  const closeSearch = () => {
    setSearchOpen(false);
    setSearchPinned(false);
  };

  const handleSearchNavigation = (item) => {
    closeSearch();
    navigate(resolveSearchNavigationRoute(item?.type));
  };

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    if (searchResults.length > 0) {
      handleSearchNavigation(searchResults[0]);
    }
  };

  const openSearchOnHover = () => {
    if (canUseHoverSearch() && !searchPinned) {
      setSearchOpen(true);
    }
  };

  const closeSearchOnLeave = () => {
    if (canUseHoverSearch() && !searchPinned) {
      setSearchOpen(false);
    }
  };

  const togglePinnedSearch = () => {
    if (searchPinned) {
      closeSearch();
      return;
    }
    setSearchPinned(true);
    setSearchOpen(true);
  };

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button onClick={toggleSidebar} className="sidebar-toggle-btn" aria-label="Alternar menu">
          <LuMenu />
        </button>
        <h1>{viewTitle || 'Dashboard'}</h1>
      </div>
      <div className="topbar-actions">
        <div
          ref={searchRef}
          className={`topbar-quick-search ${searchOpen ? 'open' : ''}`}
          onMouseEnter={openSearchOnHover}
          onMouseLeave={closeSearchOnLeave}
        >
          <button
            type="button"
            className="topbar-icon-btn topbar-search-trigger"
            aria-label="Abrir busca rápida"
            title="Busca rápida"
            onClick={togglePinnedSearch}
          >
            <LuSearch />
          </button>

          {searchOpen ? (
            <div className="topbar-search-panel" role="dialog" aria-label="Busca rápida do sistema">
              <form className="topbar-search-form" onSubmit={handleSearchSubmit}>
                <label className="topbar-search-input" htmlFor="topbar-quick-search">
                  <LuSearch />
                  <input
                    id="topbar-quick-search"
                    ref={inputRef}
                    type="text"
                    value={searchTerm}
                    onChange={(event) => setSearchTerm(event.target.value)}
                    placeholder="Buscar no sistema"
                  />
                </label>
              </form>

              <div className="topbar-search-results" role="listbox" aria-label="Resultados da busca rápida">
                {searchLoading ? (
                  <p className="topbar-search-empty">Buscando...</p>
                ) : searchResults.length > 0 ? (
                  searchResults.slice(0, 6).map((item) => (
                    <button
                      key={`${item.type}-${item.id}`}
                      type="button"
                      className="topbar-search-result-btn"
                      onClick={() => handleSearchNavigation(item)}
                    >
                      <span className="topbar-search-result-copy">
                        <strong>{item.name || 'Sem nome'}</strong>
                        <span>{formatSearchTypeLabel(item.type)}</span>
                      </span>
                      <LuArrowRight />
                    </button>
                  ))
                ) : (
                  <p className="topbar-search-empty">
                    {searchTerm.trim()
                      ? 'Nenhum resultado para a busca atual.'
                      : 'Passe o mouse ou clique na lupa para buscar qualquer item do sistema.'}
                  </p>
                )}
              </div>
            </div>
          ) : null}
        </div>

        <ThemeToggle className="theme-toggle-btn" />
        <UserMenu onLogout={logout} onNavigate={(path) => navigate(path)} />
      </div>
    </header>
  );
}

export default Topbar;
