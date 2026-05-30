import React from 'react';
import styled from 'styled-components';

const EventsContainer = styled.div`
  max-height: 520px;
  overflow: auto;
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;

  th, td {
    text-align: left;
    padding: 8px 10px;
    border-bottom: 1px solid #eee;
    font-size: 0.95em;
  }

  th {
    background: #fafafa;
    position: sticky;
    top: 0;
    z-index: 2;
  }
`;

const Empty = styled.div`
  padding: 20px;
  color: #666;
`;

function formatDuration(sec) {
  if (sec === null || sec === undefined) return '-';
  const s = Number(sec);
  if (isNaN(s)) return String(sec);
  const hours = Math.floor(s / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  const seconds = Math.floor(s % 60);
  if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

const EventsPanel = ({ events }) => {
  if (!events || events.length === 0) {
    return <Empty>No recent events.</Empty>;
  }

  return (
    <EventsContainer>
      <Table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Type</th>
            <th>Spot ID</th>
            <th>Zone</th>
            <th>Level</th>
            <th>Vehicle</th>
            <th>Occupancy</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e, idx) => (
            <tr key={e.id || idx}>
              <td>
                {e.event_timestamp
                  ? new Date(e.event_timestamp).toLocaleString()
                  : "-"}
              </td>
              <td>{e.event || "-"}</td>
              <td>{e.spot_id || "-"}</td>
              <td>{e.zone || "-"}</td>
              <td>{e.level || "-"}</td>
              <td>{e.vehicle_type || "-"}</td>
              <td>{formatDuration(e.occupancy_duration)}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </EventsContainer>
  );
};

export default EventsPanel;
