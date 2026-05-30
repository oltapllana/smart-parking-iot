import React from 'react';
import styled from 'styled-components';

const Container = styled.div`
  background: white;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
`;

const StatGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
`;

const StatBox = styled.div`
  text-align: center;
  padding: 20px;
  background: linear-gradient(135deg, ${props => props.gradient || '#667eea 0%, #764ba2 100%'});
  color: white;
  border-radius: 8px;
  
  .label {
    font-size: 0.9em;
    opacity: 0.9;
    margin-bottom: 8px;
    text-transform: uppercase;
  }
  
  .value {
    font-size: 2.5em;
    font-weight: bold;
    line-height: 1;
  }
  
  .unit {
    font-size: 0.9em;
    opacity: 0.9;
    margin-top: 4px;
  }
`;

const ProgressSection = styled.div`
  margin-top: 20px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
`;

const ProgressLabel = styled.div`
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-weight: bold;
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 30px;
  background: #e9ecef;
  border-radius: 15px;
  overflow: hidden;
  
  .fill {
    height: 100%;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    width: ${props => props.percentage}%;
    transition: width 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: 0.9em;
  }
`;

const ParkingOverview = ({ data }) => {
  if (!data) {
    return <Container>Loading...</Container>;
  }

  const occupancyRate = data.occupancy_rate || 0;
  const occupiedSpots = data.occupied_spots || 0;
  const availableSpots = data.available_spots || 0;
  const totalSpots = data.total_spots || 1;

  return (
    <Container>
      <h2>📊 Parking Lot Overview</h2>
      
      <StatGrid>
        <StatBox gradient="#667eea 0%, #764ba2 100%">
          <div className="label">Total Spots</div>
          <div className="value">{totalSpots}</div>
        </StatBox>
        
        <StatBox gradient="#f093fb 0%, #4facfe 100%">
          <div className="label">Occupied</div>
          <div className="value">{occupiedSpots}</div>
        </StatBox>
        
        <StatBox gradient="#43e97b 0%, #38f9d7 100%">
          <div className="label">Available</div>
          <div className="value">{availableSpots}</div>
        </StatBox>
        
        <StatBox gradient="#fa709a 0%, #fee140 100%">
          <div className="label">Occupancy Rate</div>
          <div className="value">{occupancyRate.toFixed(1)}%</div>
        </StatBox>
      </StatGrid>

      <ProgressSection>
        <ProgressLabel>
          <span>Parking Lot Capacity</span>
          <span>{occupancyRate.toFixed(1)}% Full</span>
        </ProgressLabel>
        <ProgressBar percentage={occupancyRate}>
          <div className="fill">
            {occupancyRate.toFixed(0)}%
          </div>
        </ProgressBar>
        
        <div style={{ marginTop: '15px', fontSize: '0.9em', color: '#666' }}>
          {occupancyRate < 50 && '✅ Plenty of availability'}
          {occupancyRate >= 50 && occupancyRate < 75 && '⚠️ Moderate availability'}
          {occupancyRate >= 75 && occupancyRate < 90 && '⚠️ Getting full'}
          {occupancyRate >= 90 && '🔴 Almost full'}
        </div>
      </ProgressSection>
    </Container>
  );
};

export default ParkingOverview;
