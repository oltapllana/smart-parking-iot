import React from 'react';
import styled from 'styled-components';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const Container = styled.div`
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-radius: 12px;
  padding: 25px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(148, 163, 184, 0.15);
  min-height: 400px;
`;

const ChartWrapper = styled.div`
  margin-top: 20px;
  width: 100%;
  height: 400px;
`;

const OccupancyChart = ({ history }) => {
  // Format data for chart
  const chartData = (history || []).map(item => ({
    time: new Date(item.timestamp).toLocaleTimeString(),
    occupancy: item.occupancy_rate?.toFixed(1),
    occupied: item.occupied_spots,
    available: item.available_spots
  }));

  // Take last 20 data points
  const displayData = chartData.slice(-20);

  return (
    <Container>
      <h3>📈 Occupancy Trend</h3>
      
      <ChartWrapper>
        {displayData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={displayData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="time" 
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis 
                yAxisId="left"
                label={{ value: 'Occupancy Rate (%)', angle: -90, position: 'insideLeft' }}
              />
              <YAxis 
                yAxisId="right"
                orientation="right"
                label={{ value: 'Spots', angle: 90, position: 'insideRight' }}
              />
              <Tooltip />
              <Legend />
              <Line 
                yAxisId="left"
                type="monotone" 
                dataKey="occupancy" 
                stroke="#667eea" 
                strokeWidth={2}
                dot={{ r: 4 }}
                name="Occupancy Rate (%)"
              />
              <Line 
                yAxisId="right"
                type="monotone" 
                dataKey="occupied" 
                stroke="#f093fb" 
                strokeWidth={2}
                dot={{ r: 4 }}
                name="Occupied Spots"
              />
              <Line 
                yAxisId="right"
                type="monotone" 
                dataKey="available" 
                stroke="#43e97b" 
                strokeWidth={2}
                dot={{ r: 4 }}
                name="Available Spots"
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div>Loading chart data...</div>
        )}
      </ChartWrapper>
    </Container>
  );
};

export default OccupancyChart;
