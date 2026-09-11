import React from 'react';
import { Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function ProgressBar({ jobStatus }) {
  if (!jobStatus) return null;

  const { status, rows_total = 0, rows_loaded = 0, rows_failed = 0, job_id } = jobStatus;
  const processed = rows_loaded + rows_failed;
  const percentage = rows_total > 0 ? Math.min(100, Math.round((processed / rows_total) * 100)) : 0;

  return (
    <div className="progress-card">
      <div className="progress-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
          {status === 'loading' && <Loader2 size={16} className="animate-spin" style={{ animation: 'spin 1.5s linear infinite' }} />}
          {status === 'complete' && <CheckCircle2 size={16} color="var(--status-success)" />}
          {status === 'failed' && <AlertTriangle size={16} color="var(--status-error)" />}
          <span style={{ fontWeight: 600, fontSize: '0.88rem' }}>
            Job: <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-secondary)' }}>{job_id}</code>
          </span>
        </div>
        <span className={`progress-status-badge ${status}`}>
          {status}
        </span>
      </div>

      <div className="progress-bar-bg">
        <div
          className="progress-bar-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>

      <div className="progress-stats-row">
        <span>
          <strong>{rows_loaded.toLocaleString()}</strong> of <strong>{rows_total.toLocaleString()}</strong> rows loaded ({percentage}%)
        </span>
        {rows_failed > 0 && (
          <span style={{ color: 'var(--status-error)' }}>
            ⚠️ {rows_failed} failed
          </span>
        )}
      </div>
    </div>
  );
}
