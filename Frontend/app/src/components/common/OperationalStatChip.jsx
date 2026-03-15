import React from 'react';

function OperationalStatChip({ icon, label, value, tone = 'neutral' }) {
  return (
    <div className={`ops-metric-chip tone-${tone}`}>
      <span className="ops-metric-chip-icon">{icon}</span>
      <div className="ops-metric-chip-copy">
        <strong>{value}</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}

export default OperationalStatChip;
