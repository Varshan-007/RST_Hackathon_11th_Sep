import React, { useState, useRef, useEffect } from 'react';
import { Send, ChevronDown, ChevronUp, Bot, User, Sparkles, CheckCircle2, AlertTriangle, Code2 } from 'lucide-react';

export default function ChatInterface({ isDatasetLoaded, detectedColumns, onSendMessage, messages, isAsking }) {
  const [inputQuestion, setInputQuestion] = useState('');
  const [expandedCypher, setExpandedCypher] = useState({});
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isAsking]);

  const toggleCypher = (idx) => {
    setExpandedCypher((prev) => ({
      ...prev,
      [idx]: !prev[idx]
    }));
  };

  const handleSend = (e) => {
    e?.preventDefault();
    if (!inputQuestion.trim() || isAsking) return;
    onSendMessage(inputQuestion.trim());
    setInputQuestion('');
  };

  const handleChipClick = (prompt) => {
    if (isAsking) return;
    onSendMessage(prompt);
  };

  // Generate dynamic prompt suggestion chips
  const promptSuggestions = [];
  promptSuggestions.push("How many rows in total?");
  if (detectedColumns && detectedColumns.length > 0) {
    const col = detectedColumns.find(c => ['department', 'group', 'city', 'role', 'status'].includes(c.toLowerCase())) || detectedColumns[0];
    promptSuggestions.push(`List distinct values of ${col}`);
    promptSuggestions.push(`Breakdown count by ${col}`);
    promptSuggestions.push(`How many rows belong to the Billing group?`);
    promptSuggestions.push("What columns are in the dataset?");
  }
  promptSuggestions.push("Who is the president of France?"); // Ungrounded test

  return (
    <div className="chat-container">
      <div className="chat-messages-area">
        {messages.length === 0 ? (
          <div className="chat-empty-state">
            <Bot size={42} style={{ opacity: 0.4 }} />
            <h4 style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Grounded Knowledge Assistant</h4>
            <p style={{ fontSize: '0.82rem', maxWidth: '360px' }}>
              {isDatasetLoaded 
                ? "Ask any question in plain English. Answers are strictly derived from real Neo4j graph data." 
                : "Upload a CSV file to unlock graph-grounded questions and Cypher translation."}
            </p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`chat-bubble ${msg.role}`}>
              {msg.role === 'user' ? (
                <div className="bubble-user-text">
                  {msg.content}
                </div>
              ) : (
                <div className="bubble-bot-card">
                  <div className="bot-card-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', fontWeight: 600 }}>
                      <Bot size={15} color="var(--accent-primary)" />
                      <span>Graph Assistant</span>
                    </div>
                    <span className={`grounded-badge ${msg.grounded ? 'grounded' : 'ungrounded'}`}>
                      {msg.grounded ? (
                        <>
                          <CheckCircle2 size={12} /> Grounded ✅
                        </>
                      ) : (
                        <>
                          <AlertTriangle size={12} /> Not Grounded ⚠️
                        </>
                      )}
                    </span>
                  </div>

                  <div className="bot-answer-text">
                    {msg.answer}
                  </div>

                  {msg.cypher && (
                    <div className="cypher-accordion">
                      <div className="cypher-accordion-header" onClick={() => toggleCypher(idx)}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          <Code2 size={14} /> Cypher Query & Graph Result
                        </span>
                        {expandedCypher[idx] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </div>

                      {expandedCypher[idx] && (
                        <div>
                          <div className="cypher-code-block">
                            {msg.cypher}
                          </div>
                          {msg.result && msg.result.length > 0 && (
                            <div className="raw-result-block">
                              <pre>{JSON.stringify(msg.result, null, 2)}</pre>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}

        {isAsking && (
          <div className="chat-bubble bot">
            <div className="bubble-bot-card" style={{ padding: '0.75rem 1rem' }}>
              <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                ⚡ Translating to Cypher & querying Neo4j...
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {isDatasetLoaded && (
        <div className="prompt-chips-row">
          {promptSuggestions.map((prompt, pIdx) => (
            <button
              key={pIdx}
              type="button"
              className="prompt-chip"
              onClick={() => handleChipClick(prompt)}
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      <form onSubmit={handleSend} className="chat-input-bar">
        <input
          type="text"
          className="chat-input-field"
          placeholder={isDatasetLoaded ? "Ask a question about the graph data..." : "Upload a CSV first to start chatting..."}
          value={inputQuestion}
          onChange={(e) => setInputQuestion(e.target.value)}
          disabled={!isDatasetLoaded || isAsking}
        />
        <button
          type="submit"
          className="chat-send-btn"
          disabled={!isDatasetLoaded || !inputQuestion.trim() || isAsking}
        >
          <Send size={16} />
          <span>Ask</span>
        </button>
      </form>
    </div>
  );
}
