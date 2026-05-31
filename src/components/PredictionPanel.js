import React from 'react';
import styled from 'styled-components';
import { TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';

const Container = styled.div`
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-radius: 12px;
  padding: 25px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(148, 163, 184, 0.15);
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
  margin-bottom: 20px;
`;

const StatCard = styled.div`
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  
  &.warning {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  }
  
  &.success {
    background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
  }
`;

const StatLabel = styled.div`
  font-size: 0.9em;
  opacity: 0.9;
  margin-bottom: 8px;
  text-transform: uppercase;
`;

const StatValue = styled.div`
  font-size: 2em;
  font-weight: bold;
`;

const TrendIndicator = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  margin-top: 10px;
  font-size: 0.9em;
  
  svg {
    width: 20px;
    height: 20px;
  }
`;

const RecommendationBox = styled.div`
  background: rgba(148, 163, 184, 0.2);
  border-left: 4px solid #667eea;
  padding: 15px;
  border-radius: 5px;
  margin-top: 15px;
  
  strong {
    color: #667eea;
  }
`;

const PredictionPanel = ({ prediction }) => {
  if (!prediction) {
    return <Container>Loading predictions...</Container>;
  }

  return (
    <Container>
      <h3>🔮 Predictions</h3>
      
      <Grid>
        <StatCard className={prediction.availability === 'HIGH' ? 'success' : prediction.availability === 'LOW' ? 'warning' : ''}>
          <StatLabel>Availability</StatLabel>
          <StatValue>{prediction.availability}</StatValue>
          <div style={{ fontSize: '0.85em', marginTop: '8px' }}>
            Confidence: {(prediction.confidence * 100).toFixed(0)}%
          </div>
        </StatCard>
        
        <StatCard>
          <StatLabel>Current Occupancy</StatLabel>
          <StatValue>{prediction.occupancy_rate?.toFixed(1) || 0}%</StatValue>
        </StatCard>
      </Grid>
      
      <RecommendationBox>
        <strong>💡 Recommendation:</strong>
        <p>{prediction.recommendation}</p>
      </RecommendationBox>

      {prediction.model && (
        <div style={{ marginTop: '12px', fontSize: '0.8em', opacity: 0.6 }}>
          🤖 Model: <strong>{prediction.model}</strong>
          {prediction.class_probabilities && (
            <span> · top class {(prediction.confidence * 100).toFixed(0)}% confidence</span>
          )}
        </div>
      )}
    </Container>
  );
};

export default PredictionPanel;
