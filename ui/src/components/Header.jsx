import React from 'react';
import HealthBadge from './HealthBadge';
import { Database, Cpu, MessageSquareQuote } from 'lucide-react';

export default function Header({ health }) {
  return (
    <header className="app-header">
      <div className="brand">
        <div className="logo-icon">
          <Database size={24} color="#ffffff" />
        </div>
        <div className="brand-text">
          <h1>Data In, Answers Out</h1>
        </div>
      </div>


      <div className="health-group">
        <HealthBadge label="API" ok={health.api} />
        <HealthBadge label="Kafka" ok={health.kafka} />
        <HealthBadge label="Neo4j" ok={health.neo4j} />
      </div>
    </header>
  );
}
