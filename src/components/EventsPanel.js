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
    padding: 12px 10px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.2);
    font-size: 0.95em;
    color: #e2e8f0;
  }

  th {
    background: rgba(59, 130, 246, 0.1);
    border-bottom: 2px solid rgba(59, 130, 246, 0.3);
    position: sticky;
    top: 0;
    z-index: 2;
    color: #60a5fa;
    font-weight: 600;
  }

  tbody tr:hover {
    background: rgba(59, 130, 246, 0.05);
  }
`;

const Empty = styled.div`
  padding: 20px;
  color: #94a3b8;
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
