import React from 'react';

export default function HealthBadge({ label, ok }) {
  return (
    <div className="health-pill" title={`${label}: ${ok ? 'Connected & Ready' : 'Disconnected / Unreachable'}`}>
      <span className={`health-dot ${ok ? 'ok' : 'error'}`}></span>
      <span>{label}</span>
    </div>
  );
}
