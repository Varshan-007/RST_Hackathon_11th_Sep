import React from 'react';
import { Table, Eye } from 'lucide-react';

export default function PreviewTable({ headers, rows, totalRows }) {
  if (!headers || headers.length === 0) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontWeight: 600 }}>
          <Eye size={14} /> Instant Client Preview
        </span>
        <span>Showing {rows.length} of {totalRows || rows.length} rows ({headers.length} columns)</span>
      </div>

      <div className="preview-wrapper">
        <table className="preview-table">
          <thead>
            <tr>
              <th style={{ width: '40px' }}>#</th>
              {headers.map((h, i) => (
                <th key={i}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rIdx) => (
              <tr key={rIdx}>
                <td style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{rIdx + 1}</td>
                {headers.map((h, cIdx) => (
                  <td key={cIdx}>
                    {row[h] !== undefined && row[h] !== null ? String(row[h]) : (
                      Array.isArray(row) ? String(row[cIdx] || '') : ''
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
