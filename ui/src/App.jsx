import React, { useState, useEffect, useRef } from 'react';
import Papa from 'papaparse';
import Header from './components/Header';
import Dropzone from './components/Dropzone';
import PreviewTable from './components/PreviewTable';
import ProgressBar from './components/ProgressBar';
import ChatInterface from './components/ChatInterface';
import { UploadCloud, MessageSquare, AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react';
import './App.css';

const API_BASE = ''; // proxied via Vite dev server or Nginx in Docker

export default function App() {
  const [health, setHealth] = useState({ api: false, kafka: false, neo4j: false });
  const [currentFile, setCurrentFile] = useState(null);
  const [previewHeaders, setPreviewHeaders] = useState([]);
  const [previewRows, setPreviewRows] = useState([]);
  const [totalParsedRows, setTotalParsedRows] = useState(0);

  const [jobStatus, setJobStatus] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  const [messages, setMessages] = useState([]);
  const [isAsking, setIsAsking] = useState(false);

  const pollingTimerRef = useRef(null);

  // Poll Health
  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok || res.status === 503) {
        const data = await res.json();
        setHealth({
          api: true,
          kafka: Boolean(data.kafka_connected),
          neo4j: Boolean(data.neo4j_connected)
        });
      } else {
        setHealth({ api: false, kafka: false, neo4j: false });
      }
    } catch {
      setHealth({ api: false, kafka: false, neo4j: false });
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 4000);
    return () => clearInterval(interval);
  }, []);

  // Poll Job Status
  const pollStatus = async (jobId) => {
    try {
      const res = await fetch(`${API_BASE}/status?job_id=${jobId}`);
      if (res.ok) {
        const data = await res.json();
        setJobStatus(data);
        if (data.status === 'complete') {
          clearInterval(pollingTimerRef.current);
          setSuccessMessage(`Dataset loaded into Neo4j successfully! (${data.rows_loaded} rows)`);
        } else if (data.status === 'failed') {
          clearInterval(pollingTimerRef.current);
          setErrorMessage(`Ingestion failed with ${data.rows_failed} errors.`);
        }
      }
    } catch (err) {
      console.warn('Error polling status:', err);
    }
  };

  const handleFileSelected = (file) => {
    setErrorMessage(null);
    setSuccessMessage(null);
    setCurrentFile(file);

    // Instant client-side parse
    Papa.parse(file, {
      preview: 20,
      skipEmptyLines: true,
      complete: (results) => {
        if (results.data && results.data.length > 0) {
          const headers = results.data[0];
          const rows = results.data.slice(1);
          setPreviewHeaders(headers);
          setPreviewRows(rows);
          setTotalParsedRows(results.data.length - 1);
        } else {
          setPreviewHeaders([]);
          setPreviewRows([]);
          setTotalParsedRows(0);
        }
      },
      error: (err) => {
        console.warn('Papa parse error:', err);
      }
    });

    // Upload to API
    uploadFile(file);
  };

  const uploadFile = async (file) => {
    setIsUploading(true);
    setJobStatus(null);
    clearInterval(pollingTimerRef.current);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/ingest`, {
        method: 'POST',
        body: formData
      });

      const data = await res.json();
      if (!res.ok) {
        setErrorMessage(data.detail || data.error || 'Failed to ingest file');
        setIsUploading(false);
        return;
      }

      // Initial job state
      setJobStatus({
        job_id: data.job_id,
        status: data.status || 'queued',
        rows_total: data.rows_received,
        rows_loaded: 0,
        rows_failed: 0
      });

      // Start polling
      pollingTimerRef.current = setInterval(() => {
        pollStatus(data.job_id);
      }, 500);

    } catch (err) {
      setErrorMessage(`Network error uploading file: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  // Load sample test data
  const handleLoadSample = async (type) => {
    setErrorMessage(null);
    setSuccessMessage(null);

    let content = '';
    let filename = '';

    if (type === 'clean') {
      filename = 'small_clean.csv';
      content = `id,name,department,role,salary,city,status
1,Alice Johnson,Engineering,Senior Software Engineer,125000,San Francisco,active
2,Bob Smith,Engineering,Software Engineer,95000,San Francisco,active
3,Carol Williams,Marketing,Marketing Lead,105000,New York,active
4,David Brown,Billing,Finance Manager,115000,Chicago,active
5,Emma Davis,Billing,Billing Analyst,75000,Chicago,active
6,Frank Miller,Billing,Billing Specialist,68000,Chicago,active
7,Grace Wilson,Sales,Account Executive,90000,Austin,active
8,Henry Taylor,Sales,Sales Representative,70000,Austin,inactive
9,Ivy Anderson,Engineering,DevOps Engineer,110000,Seattle,active
10,Jack Thomas,Support,Support Specialist,60000,Denver,active
11,Karen Jackson,Support,Support Lead,80000,Denver,active
12,Leo White,Engineering,Frontend Developer,92000,San Francisco,active
13,Mia Harris,Marketing,Content Strategist,82000,New York,active
14,Noah Martin,Sales,Sales Manager,120000,Austin,active
15,Olivia Thompson,Billing,Senior Billing Analyst,85000,Chicago,active
16,Paul Garcia,Support,Support Specialist,62000,Denver,inactive
17,Quinn Martinez,Engineering,QA Engineer,88000,Seattle,active
18,Rachel Robinson,Marketing,SEO Specialist,78000,New York,active
19,Sam Clark,Billing,Billing Analyst,74000,Chicago,active
20,Tina Rodriguez,Engineering,Engineering Manager,145000,San Francisco,active`;
    } else if (type === 'volume') {
      filename = 'medium_volume.csv';
      const rows = ['id,name,department,role,salary,city,status'];
      const depts = ['Engineering', 'Marketing', 'Billing', 'Sales', 'Support'];
      const cities = ['San Francisco', 'New York', 'Chicago', 'Austin', 'Seattle'];
      for (let i = 1; i <= 1000; i++) {
        const dept = depts[i % depts.length];
        const city = cities[i % cities.length];
        rows.push(`${i},Employee ${i},${dept},Specialist,${70000 + (i * 50) % 60000},${city},active`);
      }
      content = rows.join('\n');
    } else if (type === 'broken') {
      filename = 'broken_ragged.csv';
      content = `id,name,department,role,salary,city,status
1,Broken Row One,Only,Two
2,Broken Row Two,Engineering,Developer,90000,San Francisco,active,extra1,extra2
3,"Unclosed quote,Broken Department,100000
4,Valid Row,Marketing,Lead,95000,New York,active`;
    } else if (type === 'header_only') {
      filename = 'header_only.csv';
      content = 'id,name,department,role,salary,city,status\n';
    } else if (type === 'empty') {
      filename = 'empty.csv';
      content = '';
    }

    const file = new File([content], filename, { type: 'text/csv' });
    handleFileSelected(file);
  };

  // Chat message submission
  const handleSendMessage = async (question) => {
    setIsAsking(true);
    const newMessages = [...messages, { role: 'user', content: question }];
    setMessages(newMessages);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });

      const data = await res.json();
      if (!res.ok) {
        setMessages([
          ...newMessages,
          {
            role: 'bot',
            answer: data.detail || 'Error processing question.',
            cypher: '',
            result: [],
            grounded: false
          }
        ]);
      } else {
        setMessages([
          ...newMessages,
          {
            role: 'bot',
            answer: data.answer,
            cypher: data.cypher,
            result: data.result,
            grounded: data.grounded
          }
        ]);
      }
    } catch (err) {
      setMessages([
        ...newMessages,
        {
          role: 'bot',
          answer: `Network error reaching chat endpoint: ${err.message}`,
          cypher: '',
          result: [],
          grounded: false
        }
      ]);
    } finally {
      setIsAsking(false);
    }
  };

  const isDatasetLoaded = Boolean(jobStatus && jobStatus.status === 'complete') || totalParsedRows > 0;

  return (
    <div className="app-container">
      <Header health={health} />

      {errorMessage && (
        <div className="alert-box error">
          <AlertTriangle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {successMessage && (
        <div className="alert-box info">
          <CheckCircle2 size={18} />
          <span>{successMessage}</span>
        </div>
      )}

      <main className="main-grid">
        {/* Left Column: Ingest & Preview */}
        <section className="glass-panel">
          <div className="panel-header">
            <h2 className="panel-title">
              <UploadCloud size={20} color="var(--accent-primary)" />
              <span>Data Ingest Pipeline</span>
            </h2>
          </div>

          <Dropzone
            onFileSelected={handleFileSelected}
            isUploading={isUploading}
            currentFile={currentFile}
            onLoadSample={handleLoadSample}
          />

          {jobStatus && <ProgressBar jobStatus={jobStatus} />}

          {previewHeaders.length > 0 && (
            <PreviewTable
              headers={previewHeaders}
              rows={previewRows}
              totalRows={totalParsedRows}
            />
          )}
        </section>

        {/* Right Column: Grounded Graph Chat */}
        <section className="glass-panel">
          <div className="panel-header">
            <h2 className="panel-title">
              <MessageSquare size={20} color="var(--accent-secondary)" />
              <span>Grounded Chatbot</span>
            </h2>
          </div>

          <ChatInterface
            isDatasetLoaded={isDatasetLoaded}
            detectedColumns={previewHeaders}
            onSendMessage={handleSendMessage}
            messages={messages}
            isAsking={isAsking}
          />
        </section>
      </main>
    </div>
  );
}
