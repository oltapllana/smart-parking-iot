import React from 'react';
import styled from 'styled-components';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const Container = styled.div`
  background: white;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
`;

const ZoneGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
`;

const ZoneCard = styled.div`
  background: linear-gradient(135deg, ${props => props.color || '#667eea'} 0%, ${props => props.darkColor || '#764ba2'} 100%);
  color: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
`;

const ZoneName = styled.h4`
  margin: 0 0 15px 0;
  font-size: 1.2em;
`;

const ZoneStats = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 10px;
`;

const StatItem = styled.div`
  background: rgba(255, 255, 255, 0.2);
  padding: 10px;
  border-radius: 5px;
  text-align: center;
  
  .label {
    font-size: 0.9em;
    opacity: 0.9;
  }
  
  .value {
    font-size: 1.4em;
    font-weight: bold;
  }
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 4px;
  overflow: hidden;
  margin-top: 10px;
  
  .fill {
    height: 100%;
    background: rgba(255, 255, 255, 0.8);
    width: ${props => props.percentage}%;
    transition: width 0.3s ease;
  }
`;

const colors = [
  { color: '#667eea', darkColor: '#764ba2' },
  { color: '#f093fb', darkColor: '#4facfe' },
  { color: '#43e97b', darkColor: '#38f9d7' },
  { color: '#fa709a', darkColor: '#fee140' }
];

const ZoneStatus = ({ zones }) => {
  const zoneData = Object.entries(zones || {}).map(([name, stats], idx) => ({
    name,
    ...stats,
    color: colors[idx % colors.length]
  }));

  const chartData = zoneData.map(zone => ({
    name: zone.name,
    'Available': zone.available,
    'Occupied': zone.occupied
  }));

  return (
    <Container>
      <h2>🚗 Zone Status</h2>
      
      <ZoneGrid>
        {zoneData.map(zone => (
          <ZoneCard key={zone.name} color={zone.color.color} darkColor={zone.color.darkColor}>
            <ZoneName>{zone.name}</ZoneName>
            <ZoneStats>
              <StatItem>
                <div className="label">Occupied</div>
                <div className="value">{zone.occupied}</div>
              </StatItem>
              <StatItem>
                <div className="label">Available</div>
                <div className="value">{zone.available}</div>
              </StatItem>
            </ZoneStats>
            <ProgressBar percentage={zone.occupancy_rate}>
              <div className="fill" />
            </ProgressBar>
            <p style={{ margin: '8px 0 0 0', fontSize: '0.9em' }}>
              {zone.occupancy_rate.toFixed(1)}% Full
            </p>
          </ZoneCard>
        ))}
      </ZoneGrid>

      <h3>📊 Zone Comparison</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="Occupied" stackId="a" fill="#667eea" />
          <Bar dataKey="Available" stackId="a" fill="#43e97b" />
        </BarChart>
      </ResponsiveContainer>
    </Container>
  );
};

export default ZoneStatus;
