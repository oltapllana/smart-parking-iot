import React from 'react';
import styled from 'styled-components';
import { AlertCircle, AlertTriangle, Info } from 'lucide-react';

const Container = styled.div`
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-radius: 12px;
  padding: 25px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(148, 163, 184, 0.15);
`;

const AlertList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 10px;
`;

const AlertItem = styled.div`
  display: flex;
  gap: 12px;
  padding: 15px;
  border-radius: 8px;
  background: ${props => {
    switch (props.severity) {
      case 'critical': return 'rgba(239, 68, 68, 0.1)';
      case 'warning': return 'rgba(245, 158, 11, 0.1)';
      case 'info': return 'rgba(59, 130, 246, 0.1)';
      default: return 'rgba(148, 163, 184, 0.1)';
    }
  }};
  border-left: 4px solid ${props => {
    switch (props.severity) {
      case 'critical': return '#ef4444';
      case 'warning': return '#f59e0b';
      case 'info': return '#3b82f6';
      default: return '#94a3b8';
    }
  }};
  border: 1px solid ${props => {
    switch (props.severity) {
      case 'critical': return 'rgba(239, 68, 68, 0.3)';
      case 'warning': return 'rgba(245, 158, 11, 0.3)';
      case 'info': return 'rgba(59, 130, 246, 0.3)';
      default: return 'rgba(148, 163, 184, 0.2)';
    }
  }};
`;

const AlertIcon = styled.div`
  flex-shrink: 0;
  display: flex;
  align-items: center;
  
  svg {
    width: 24px;
    height: 24px;
    color: ${props => {
      switch (props.severity) {
        case 'critical': return '#ef4444';
        case 'warning': return '#f59e0b';
        case 'info': return '#3b82f6';
        default: return '#94a3b8';
      }
    }};
  }
`;

const AlertContent = styled.div`
  flex: 1;
  color: #e2e8f0;
  
  .title {
    font-weight: bold;
    margin-bottom: 4px;
    text-transform: capitalize;
    color: ${props => {
      switch (props.severity) {
        case 'critical': return '#fca5a5';
        case 'warning': return '#fbbf24';
        case 'info': return '#93c5fd';
        default: return '#cbd5e1';
      }
    }};
  }
  
  .message {
    font-size: 0.95em;
    opacity: 0.8;
  }
  
  .timestamp {
    font-size: 0.85em;
    opacity: 0.6;
    margin-top: 4px;
  }
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 40px 20px;
  color: #94a3b8;
  
  svg {
    width: 50px;
    height: 50px;
    margin-bottom: 15px;
    opacity: 0.5;
    color: #64748b;
  }
`;

const AlertPanel = ({ alerts }) => {
  if (!alerts || alerts.length === 0) {
    return (
      <Container>
        <h3>🚨 Active Alerts</h3>
        <EmptyState>
          <Info />
          <p>No active alerts. Parking lot is operating normally.</p>
        </EmptyState>
      </Container>
    );
  }

  const getIcon = (severity) => {
    switch (severity) {
      case 'critical': return <AlertCircle />;
      case 'warning': return <AlertTriangle />;
      default: return <Info />;
    }
  };

  return (
    <Container>
      <h3>🚨 Active Alerts ({alerts.length})</h3>
      <AlertList>
        {alerts.map(alert => (
          <AlertItem key={alert.id} severity={alert.severity}>
            <AlertIcon severity={alert.severity}>
              {getIcon(alert.severity)}
            </AlertIcon>
            <AlertContent>
              <div className="title">{alert.type.replace(/_/g, ' ')}</div>
              <div className="message">{alert.message}</div>
              <div className="timestamp">
                {new Date(alert.timestamp).toLocaleTimeString()}
              </div>
            </AlertContent>
          </AlertItem>
        ))}
      </AlertList>
    </Container>
  );
};

export default AlertPanel;
