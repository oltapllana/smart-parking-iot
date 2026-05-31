import React from 'react';
import styled from 'styled-components';
import { Gauge, Clock, Activity, Database, CheckCircle } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 18px;
  margin: 20px 0;
`;

const MetricCard = styled.div`
  background: linear-gradient(135deg, ${p => p.color}22 0%, ${p => p.color}11 100%);
  border: 1px solid ${p => p.color}55;
  border-radius: 10px;
  padding: 18px;
  display: flex;
  align-items: center;
  gap: 14px;
`;

const IconBox = styled.div`
  width: 44px; height: 44px;
  display: flex; align-items: center; justify-content: center;
  background: ${p => p.color}; border-radius: 8px; color: #fff;
`;

const MetricLabel = styled.div`
  font-size: 0.8em; opacity: 0.7; text-transform: uppercase; letter-spacing: 0.5px;
`;

const MetricValue = styled.div`
  font-size: 1.6em; font-weight: 700; color: ${p => p.color || '#e2e8f0'};
`;

const Section = styled.div`
  margin-top: 25px;
`;

const Table = styled.table`
  width: 100%; border-collapse: collapse; margin-top: 10px;
  th { background: rgba(59,130,246,0.1); color: #60a5fa; padding: 10px; text-align: left; }
  td { padding: 10px; border-bottom: 1px solid rgba(148,163,184,0.15); color: #e2e8f0; }
  tr:hover { background: rgba(148,163,184,0.05); }
`;

const Badge = styled.span`
  padding: 3px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 600;
  background: ${p => p.ok ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'};
  color: ${p => p.ok ? '#10b981' : '#ef4444'};
`;

const PerformancePanel = ({ performance, windows }) => {
  if (!performance || !performance.counters) {
    return <div>Loading performance metrics…</div>;
  }

  const { throughput, latency, counters, health, uptime_seconds } = performance;

  const windowChart = (windows || [])
    .slice()
    .reverse()
    .map(w => ({
      time: (w.window_start || '').slice(11, 16),
      events: w.event_count,
      entries: w.entries,
      exits: w.exits,
    }));

  return (
    <div>
      <h3 style={{ marginTop: 0 }}>📊 Performance Analysis & Optimization</h3>
      <p style={{ opacity: 0.7, marginTop: 4 }}>
        Live throughput and latency measured across the Kafka → Spark → Cassandra
        pipeline. Uptime: {uptime_seconds}s ·{' '}
        <Badge ok={health.status === 'healthy'}>{health.status}</Badge>
      </p>

      <Grid>
        <MetricCard color="#3b82f6">
          <IconBox color="#3b82f6"><Gauge size={24} /></IconBox>
          <div>
            <MetricLabel>Spark Throughput</MetricLabel>
            <MetricValue color="#60a5fa">{throughput.spark_eps} eps</MetricValue>
          </div>
        </MetricCard>

        <MetricCard color="#f59e0b">
          <IconBox color="#f59e0b"><Clock size={24} /></IconBox>
          <div>
            <MetricLabel>End-to-End Latency</MetricLabel>
            <MetricValue color="#fbbf24">{latency.end_to_end_ms} ms</MetricValue>
          </div>
        </MetricCard>

        <MetricCard color="#8b5cf6">
          <IconBox color="#8b5cf6"><Database size={24} /></IconBox>
          <div>
            <MetricLabel>Cassandra Write p95</MetricLabel>
            <MetricValue color="#a78bfa">{latency.cassandra_write.p95_ms} ms</MetricValue>
          </div>
        </MetricCard>

        <MetricCard color="#10b981">
          <IconBox color="#10b981"><CheckCircle size={24} /></IconBox>
          <div>
            <MetricLabel>Data Quality</MetricLabel>
            <MetricValue color="#34d399">{health.data_quality_pct}%</MetricValue>
          </div>
        </MetricCard>
      </Grid>

      <Section>
        <h4 style={{ marginBottom: 6 }}>⏱️ Per-Stage Latency (ms)</h4>
        <Table>
          <thead>
            <tr><th>Stage</th><th>Avg</th><th>p95</th><th>Max</th><th>Samples</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>⚡ Spark processing (end-to-end)</td>
              <td>{latency.spark_processing.avg_ms}</td>
              <td>{latency.spark_processing.p95_ms}</td>
              <td>{latency.spark_processing.max_ms}</td>
              <td>{latency.spark_processing.samples}</td>
            </tr>
            <tr>
              <td>💾 Cassandra write</td>
              <td>{latency.cassandra_write.avg_ms}</td>
              <td>{latency.cassandra_write.p95_ms}</td>
              <td>{latency.cassandra_write.max_ms}</td>
              <td>{latency.cassandra_write.samples}</td>
            </tr>
            <tr>
              <td>🌐 API response</td>
              <td>{latency.api_response.avg_ms}</td>
              <td>{latency.api_response.p95_ms}</td>
              <td>{latency.api_response.max_ms}</td>
              <td>{latency.api_response.samples}</td>
            </tr>
          </tbody>
        </Table>
      </Section>

      <Section>
        <h4 style={{ marginBottom: 6 }}>📈 Event Counters</h4>
        <Table>
          <tbody>
            <tr><td>📡 Kafka messages</td><td>{counters.kafka_messages}</td></tr>
            <tr><td>⚡ Spark processed</td><td>{counters.spark_processed}</td></tr>
            <tr><td>💾 Cassandra events</td><td>{counters.cassandra_events}</td></tr>
            <tr><td>🌐 API requests</td><td>{counters.api_requests}</td></tr>
            <tr><td>❌ Errors</td><td>{counters.errors} ({health.error_rate_pct}%)</td></tr>
          </tbody>
        </Table>
      </Section>

      {windowChart.length > 0 && (
        <Section>
          <h4 style={{ marginBottom: 6 }}>🪟 Spark Sliding-Window Aggregations (per minute)</h4>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={windowChart}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" />
              <XAxis dataKey="time" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0' }} />
              <Bar dataKey="entries" stackId="a" fill="#10b981" name="Entries" />
              <Bar dataKey="exits" stackId="a" fill="#ef4444" name="Exits" />
            </BarChart>
          </ResponsiveContainer>
        </Section>
      )}
    </div>
  );
};

export default PerformancePanel;
