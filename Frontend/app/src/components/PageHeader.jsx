/**
 * Contextual page header rendered by each page (not the layout shell).
 */

import React from 'react';
import './PageHeader.css';

function PageHeader({ title, subtitle, actions, filters }) {
  return (
    <div className="page-header">
      <div className="page-header-main">
        <div className="page-header-copy">
          <h1 className="page-header-title">{title}</h1>
          {subtitle ? <p className="page-header-subtitle">{subtitle}</p> : null}
        </div>
        {actions ? <div className="page-header-actions">{actions}</div> : null}
      </div>
      {filters ? <div className="page-header-filters">{filters}</div> : null}
    </div>
  );
}

export default PageHeader;
