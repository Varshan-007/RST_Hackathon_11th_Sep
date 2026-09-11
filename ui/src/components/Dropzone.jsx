import React, { useRef, useState } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertCircle } from 'lucide-react';

export default function Dropzone({ onFileSelected, isUploading, currentFile, onLoadSample }) {
  const fileInputRef = useRef(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileSelected(e.target.files[0]);
    }
  };

  return (
    <div>
      <div
        className={`dropzone-container ${isDragOver ? 'active' : ''}`}
        onDragOver={(e) => e.preventDefault()}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current && fileInputRef.current.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          className="file-input-hidden"
          accept=".csv,text/csv"
          onChange={handleFileInputChange}
        />

        <div className="dropzone-icon">
          <UploadCloud size={28} />
        </div>

        <div className="dropzone-text">
          {currentFile ? (
            <>
              <h3>{currentFile.name}</h3>
              <p>{(currentFile.size / 1024).toFixed(1)} KB · Click or drag to replace</p>
            </>
          ) : (
            <>
              <h3>Drop your CSV file here, or click to browse</h3>
              <p>Supports dynamic headers, streaming row ingestion into Kafka & Neo4j</p>
            </>
          )}
        </div>
      </div>

      <div className="sample-files-row">
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Quick Load Tests:</span>
        <button
          type="button"
          className="sample-btn"
          onClick={() => onLoadSample('clean')}
        >
          ✨ Clean 20 Rows
        </button>
        <button
          type="button"
          className="sample-btn"
          onClick={() => onLoadSample('volume')}
        >
          🚀 1,000 Rows Volume
        </button>
        <button
          type="button"
          className="sample-btn"
          onClick={() => onLoadSample('broken')}
        >
          ⚠️ Broken Ragged CSV
        </button>
        <button
          type="button"
          className="sample-btn"
          onClick={() => onLoadSample('header_only')}
        >
          🚫 Header-Only CSV
        </button>
        <button
          type="button"
          className="sample-btn"
          onClick={() => onLoadSample('empty')}
        >
          📭 Empty File (0B)
        </button>
      </div>
    </div>
  );
}
