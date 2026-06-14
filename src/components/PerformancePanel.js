import React from 'react';
import styled from 'styled-components';
import { Activity, Clock, Database, Lightbulb, Waves } from 'lucide-react';

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 18px;
  margin: 20px 0;
`;

const MetricCard = styled.div`
  background: linear-gradient(135deg, ${p => p.color}22 0%, ${p => p.color}11 100%);
  border: 1px solid ${p => p.color}55;
  border-radius: 8px;
  padding: 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 84px;
`;

const IconBox = styled.div`
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: ${p => p.color};
  border-radius: 8px;
  color: #fff;
  flex: 0 0 44px;
`;

const MetricLabel = styled.div`
  font-size: 0.8em;
  opacity: 0.7;
  text-transform: uppercase;
  letter-spacing: 0;
`;

const MetricValue = styled.div`
  font-size: 1.45em;
  font-weight: 700;
  color: ${p => p.color || '#e2e8f0'};
  overflow-wrap: anywhere;
`;

const Section = styled.div`
  margin-top: 25px;
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;

  th {
    background: rgba(59, 130, 246, 0.1);
    color: #60a5fa;
    padding: 10px;
    text-align: left;
  }

  td {
    padding: 10px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.15);
    color: #e2e8f0;
    overflow-wrap: anywhere;
  }

  tr:hover {
    background: rgba(148, 163, 184, 0.05);
  }
`;

const Badge = styled.span`
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.82em;
  font-weight: 700;
  text-transform: uppercase;
  background: ${p => p.status === 'healthy'
    ? 'rgba(16, 185, 129, 0.2)'
    : p.status === 'stale'
      ? 'rgba(245, 158, 11, 0.2)'
      : 'rgba(239, 68, 68, 0.2)'};
  color: ${p => p.status === 'healthy'
    ? '#34d399'
    : p.status === 'stale'
      ? '#fbbf24'
      : '#f87171'};
`;

const Recommendation = styled.div`
  display: flex;
  gap: 12px;
  align-items: flex-start;
  border-left: 3px solid #38bdf8;
  background: rgba(56, 189, 248, 0.08);
  padding: 14px 16px;
  border-radius: 8px;
  color: #e0f2fe;
`;

const formatNumber = value => {
  if (value === null || value === undefined) return 'N/A';
  return Number(value).toLocaleString();
};

const formatSeconds = value => {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return 'N/A';
  return `${value}s`;
};

const formatMs = value => {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return 'N/A';
  return `${value} ms`;
};

const formatTimestamp = value => {
  if (!value) return 'N/A';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
};

const PerformancePanel = ({ performance }) => {
  if (!performance) {
    return <div>Loading performance metrics...</div>;
  }

  const status = performance.health_status || 'error';
  const apiLatency = performance.api_latency || {};

  return (
    <div>
      <h3 style={{ marginTop: 0 }}>Performance Analysis & Optimization</h3>
      <p style={{ opacity: 0.7, marginTop: 4 }}>
        Cassandra-backed pipeline metrics polled every 5 seconds. Status:{' '}
        <Badge status={status}>{status}</Badge>
      </p>

      <Grid>
        <MetricCard color="#3b82f6">
          <IconBox color="#3b82f6"><Database size={24} /></IconBox>
          <div>
            <MetricLabel>Total Cassandra Events</MetricLabel>
            <MetricValue color="#60a5fa">{formatNumber(performance.total_cassandra_events)}</MetricValue>
          </div>
        </MetricCard>

        <MetricCard color="#8b5cf6">
          <IconBox color="#8b5cf6"><Waves size={24} /></IconBox>
          <div>
            <MetricLabel>Spark Window Aggregations</MetricLabel>
            <MetricValue color="#a78bfa">{formatNumber(performance.total_spark_window_aggregations)}</MetricValue>
          </div>
        </MetricCard>

        <MetricCard color="#10b981">
          <IconBox color="#10b981"><Activity size={24} /></IconBox>
          <div>
            <MetricLabel>Data Freshness</MetricLabel>
            <MetricValue color="#34d399">{formatSeconds(performance.data_freshness_seconds)}</MetricValue>
          </div>
        </MetricCard>

        <MetricCard color="#f59e0b">
          <IconBox color="#f59e0b"><Clock size={24} /></IconBox>
          <div>
            <MetricLabel>API Latency</MetricLabel>
            <MetricValue color="#fbbf24">{formatMs(performance.api_latency_ms)}</MetricValue>
          </div>
        </MetricCard>
      </Grid>

      <Section>
        <Recommendation>
          <Lightbulb size={20} />
          <div>{performance.optimization_recommendation || 'No recommendation available.'}</div>
        </Recommendation>
      </Section>

      <Section>
        <h4 style={{ marginBottom: 6 }}>Freshness Details</h4>
        <Table>
          <tbody>
            <tr><td>Latest event timestamp</td><td>{formatTimestamp(performance.latest_event_timestamp)}</td></tr>
            <tr><td>Latest window timestamp</td><td>{formatTimestamp(performance.latest_window_timestamp)}</td></tr>
            <tr><td>Latest event freshness</td><td>{formatSeconds(performance.latest_event_freshness_seconds)}</td></tr>
            <tr><td>Latest window freshness</td><td>{formatSeconds(performance.latest_window_freshness_seconds)}</td></tr>
            <tr><td>Freshness threshold</td><td>{formatSeconds(performance.freshness_threshold_seconds)}</td></tr>
          </tbody>
        </Table>
      </Section>

      <Section>
        <h4 style={{ marginBottom: 6 }}>API Latency Samples</h4>
        <Table>
          <thead>
            <tr><th>Current</th><th>Average</th><th>p95</th><th>Max</th><th>Samples</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>{formatMs(performance.api_latency_ms)}</td>
              <td>{formatMs(apiLatency.avg_ms)}</td>
              <td>{formatMs(apiLatency.p95_ms)}</td>
              <td>{formatMs(apiLatency.max_ms)}</td>
              <td>{apiLatency.samples ?? 0}</td>
            </tr>
          </tbody>
        </Table>
      </Section>

      {performance.error && (
        <Section>
          <Recommendation>{performance.error}</Recommendation>
        </Section>
      )}
    </div>
  );
};

export default PerformancePanel;
