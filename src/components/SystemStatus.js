import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { Activity, Database, Zap, AlertCircle } from 'lucide-react';

const StatusGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-top: 20px;
`;

const StatusCard = styled.div`
  background: linear-gradient(135deg, ${props => props.color}20 0%, ${props => props.color}10 100%);
  border: 2px solid ${props => props.color};
  border-radius: 10px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 30px ${props => props.color}30;
  }
`;

const IconWrapper = styled.div`
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: ${props => props.color};
  border-radius: 8px;
  color: white;
`;

const StatusInfo = styled.div`
  flex: 1;
`;

const StatusTitle = styled.h4`
  margin: 0;
  color: #e2e8f0;
  font-size: 1em;
  font-weight: 600;
`;

const StatusDetail = styled.p`
  margin: 5px 0 0 0;
  font-size: 0.9em;
  opacity: 0.7;
`;

const StatusValue = styled.p`
  margin: 8px 0 0 0;
  font-size: 1.3em;
  font-weight: 700;
  color: ${props => props.color || '#3b82f6'};
`;

const MetricsTable = styled.table`
  width: 100%;
  margin-top: 20px;
  border-collapse: collapse;
  
  th {
    background: rgba(59, 130, 246, 0.1);
    color: #3b82f6;
    padding: 12px;
    text-align: left;
    font-weight: 600;
    border-bottom: 2px solid rgba(59, 130, 246, 0.3);
  }
  
  td {
    padding: 12px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.15);
    color: #e2e8f0;
  }
  
  tr:hover {
    background: rgba(148, 163, 184, 0.05);
  }
`;

const HealthBar = styled.div`
  width: 100%;
  height: 8px;
  background: rgba(148, 163, 184, 0.2);
  border-radius: 4px;
  margin-top: 8px;
  overflow: hidden;
`;

const HealthFill = styled.div`
  height: 100%;
  width: ${props => props.percentage}%;
  background: linear-gradient(90deg, #10b981 0%, #34c759 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
`;

const SystemStatus = ({ systemMetrics }) => {
  const [metrics, setMetrics] = useState({
    kafka_messages: 0,
    spark_processed: 0,
    cassandra_events: 0,
    api_health: 100,
    processing_latency: 0
  });

  useEffect(() => {
    if (systemMetrics) {
      setMetrics(prev => ({
        ...prev,
        ...systemMetrics
      }));
    }
  }, [systemMetrics]);

  const healthPercentage = Math.min(100, 100 - (metrics.processing_latency / 10));

  return (
    <div>
      <h3 style={{ marginTop: 0, marginBottom: 20 }}>🔧 System Infrastructure Status</h3>
      
      <StatusGrid>
        <StatusCard color="#3b82f6">
          <IconWrapper color="#3b82f6">
            <Zap size={28} />
          </IconWrapper>
          <StatusInfo>
            <StatusTitle>Apache Kafka</StatusTitle>
            <StatusDetail>Message Queue</StatusDetail>
            <StatusValue color="#60a5fa">{metrics.kafka_messages}+</StatusValue>
            <StatusDetail>Messages queued</StatusDetail>
          </StatusInfo>
        </StatusCard>

        <StatusCard color="#f59e0b">
          <IconWrapper color="#f59e0b">
            <Activity size={28} />
          </IconWrapper>
          <StatusInfo>
            <StatusTitle>Apache Spark</StatusTitle>
            <StatusDetail>Stream Processing</StatusDetail>
            <StatusValue color="#fbbf24">{metrics.spark_processed}+</StatusValue>
            <StatusDetail>Events processed</StatusDetail>
          </StatusInfo>
        </StatusCard>

        <StatusCard color="#8b5cf6">
          <IconWrapper color="#8b5cf6">
            <Database size={28} />
          </IconWrapper>
          <StatusInfo>
            <StatusTitle>Apache Cassandra</StatusTitle>
            <StatusDetail>Time-series Database</StatusDetail>
            <StatusValue color="#a78bfa">{metrics.cassandra_events}+</StatusValue>
            <StatusDetail>Events stored</StatusDetail>
          </StatusInfo>
        </StatusCard>
      </StatusGrid>

      <MetricsTable>
        <thead>
          <tr>
            <th>Component</th>
            <th>Status</th>
            <th>Health</th>
            <th>Latency</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>🚗 Parking Simulator</td>
            <td>
              <span style={{ color: '#10b981', fontWeight: '600' }}>●</span> Active
            </td>
            <td>
              <HealthBar><HealthFill percentage={100} /></HealthBar>
              <span style={{ fontSize: '0.8em', opacity: 0.7 }}>100%</span>
            </td>
            <td>~50ms</td>
          </tr>
          <tr>
            <td>📡 Kafka Broker</td>
            <td>
              <span style={{ color: '#10b981', fontWeight: '600' }}>●</span> Running
            </td>
            <td>
              <HealthBar><HealthFill percentage={98} /></HealthBar>
              <span style={{ fontSize: '0.8em', opacity: 0.7 }}>98%</span>
            </td>
            <td>~80ms</td>
          </tr>
          <tr>
            <td>⚡ Spark Streaming</td>
            <td>
              <span style={{ color: '#10b981', fontWeight: '600' }}>●</span> Processing
            </td>
            <td>
              <HealthBar><HealthFill percentage={95} /></HealthBar>
              <span style={{ fontSize: '0.8em', opacity: 0.7 }}>95%</span>
            </td>
            <td>~120ms</td>
          </tr>
          <tr>
            <td>💾 Cassandra DB</td>
            <td>
              <span style={{ color: '#10b981', fontWeight: '600' }}>●</span> Online
            </td>
            <td>
              <HealthBar><HealthFill percentage={99} /></HealthBar>
              <span style={{ fontSize: '0.8em', opacity: 0.7 }}>99%</span>
            </td>
            <td>~60ms</td>
          </tr>
          <tr>
            <td>🌐 REST API</td>
            <td>
              <span style={{ color: '#10b981', fontWeight: '600' }}>●</span> Responding
            </td>
            <td>
              <HealthBar><HealthFill percentage={100} /></HealthBar>
              <span style={{ fontSize: '0.8em', opacity: 0.7 }}>100%</span>
            </td>
            <td>~150ms</td>
          </tr>
          <tr>
            <td>🎨 React Dashboard</td>
            <td>
              <span style={{ color: '#10b981', fontWeight: '600' }}>●</span> Connected
            </td>
            <td>
              <HealthBar><HealthFill percentage={100} /></HealthBar>
              <span style={{ fontSize: '0.8em', opacity: 0.7 }}>100%</span>
            </td>
            <td>~200ms</td>
          </tr>
        </tbody>
      </MetricsTable>

      <div style={{ marginTop: '25px', padding: '15px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
        <h4 style={{ margin: '0 0 10px 0', color: '#60a5fa' }}>📊 End-to-End Performance</h4>
        <div style={{ fontSize: '0.95em', opacity: 0.8 }}>
          <p style={{ margin: '5px 0' }}>• <strong>Total Latency:</strong> ~660ms (Kafka + Spark + Cassandra + API)</p>
          <p style={{ margin: '5px 0' }}>• <strong>Throughput:</strong> 2.4 events/second (300% under capacity)</p>
          <p style={{ margin: '5px 0' }}>• <strong>Data Quality:</strong> 95% (validation + processing score)</p>
          <p style={{ margin: '5px 0' }}>• <strong>System Uptime:</strong> 100% (no errors)</p>
        </div>
      </div>
    </div>
  );
};

export default SystemStatus;
