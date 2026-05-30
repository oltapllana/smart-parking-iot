import React from 'react';
import styled from 'styled-components';
import { AlertCircle, AlertTriangle, Info } from 'lucide-react';

const Container = styled.div`
  background: white;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
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
      case 'critical': return '#fee';
      case 'warning': return '#fef3cd';
      case 'info': return '#e7f3ff';
      default: return '#f5f5f5';
    }
  }};
  border-left: 4px solid ${props => {
    switch (props.severity) {
      case 'critical': return '#dc3545';
      case 'warning': return '#ffc107';
      case 'info': return '#0dcaf0';
      default: return '#999';
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
        case 'critical': return '#dc3545';
        case 'warning': return '#ffc107';
        case 'info': return '#0dcaf0';
        default: return '#999';
      }
    }};
  }
`;

const AlertContent = styled.div`
  flex: 1;
  
  .title {
    font-weight: bold;
    margin-bottom: 4px;
    text-transform: capitalize;
  }
  
  .message {
    font-size: 0.95em;
  }
  
  .timestamp {
    font-size: 0.85em;
    opacity: 0.7;
    margin-top: 4px;
  }
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 40px 20px;
  color: #666;
  
  svg {
    width: 50px;
    height: 50px;
    margin-bottom: 15px;
    opacity: 0.5;
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
