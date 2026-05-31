import React from 'react';
import styled from 'styled-components';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const Wrapper = styled.div`
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-radius: 12px;
  padding: 25px;
  border: 1px solid rgba(148, 163, 184, 0.15);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);

  h2 {
    margin: 0 0 20px 0;
    color: #e2e8f0;
  }

  .leaflet-container {
    border-radius: 10px;
    border: 1px solid rgba(148, 163, 184, 0.25);
  }
`;

const Legend = styled.div`
  display: flex;
  gap: 24px;
  margin-top: 16px;
  flex-wrap: wrap;
`;

const LegendItem = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9em;
  color: #cbd5e1;

  .dot {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: ${props => props.color};
    flex-shrink: 0;
  }
`;

const ZoneGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-top: 20px;
`;

const ZoneCard = styled.div`
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid ${props => props.borderColor || 'rgba(148,163,184,0.2)'};
  border-radius: 8px;
  padding: 14px;
  text-align: center;

  .zone-name {
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 6px;
    font-size: 0.9em;
  }

  .occ-value {
    font-size: 1.8em;
    font-weight: 700;
    color: ${props => props.color || '#10b981'};
    line-height: 1;
  }

  .occ-label {
    font-size: 0.78em;
    color: #94a3b8;
    margin-top: 4px;
  }

  .spots {
    font-size: 0.82em;
    color: #64748b;
    margin-top: 6px;
  }
`;

// Approximate zone positions around a Prishtina city-centre parking lot
const ZONE_COORDS = {
  'Zone-1': [42.6633, 21.1648],
  'Zone-2': [42.6633, 21.1662],
  'Zone-3': [42.6625, 21.1648],
  'Zone-4': [42.6625, 21.1662],
};

const LOT_CENTER = [42.6629, 21.1655];

function occupancyColor(rate) {
  if (rate >= 90) return '#ef4444';
  if (rate >= 75) return '#f59e0b';
  return '#10b981';
}

function occupancyStatus(rate) {
  if (rate >= 90) return 'Critical';
  if (rate >= 75) return 'Warning';
  return 'Available';
}

const ParkingMap = ({ zones }) => {
  const zoneEntries = zones ? Object.entries(zones) : [];

  return (
    <Wrapper>
      <h2>🗺️ Parking Lot Map — Prishtina</h2>

      <MapContainer
        center={LOT_CENTER}
        zoom={17}
        style={{ height: '420px' }}
        scrollWheelZoom
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {zoneEntries.map(([zoneName, stats]) => {
          const coords = ZONE_COORDS[zoneName] || LOT_CENTER;
          const occ    = stats.occupancy_rate || 0;
          const color  = occupancyColor(occ);

          return (
            <CircleMarker
              key={zoneName}
              center={coords}
              radius={28}
              pathOptions={{
                color:       color,
                fillColor:   color,
                fillOpacity: 0.55,
                weight:      2,
              }}
            >
              <Popup>
                <div style={{ minWidth: '140px' }}>
                  <strong style={{ fontSize: '1.05em' }}>{zoneName}</strong>
                  <hr style={{ margin: '6px 0' }} />
                  <div>Occupancy: <strong>{occ.toFixed(1)}%</strong></div>
                  <div>Occupied:  <strong>{stats.occupied}</strong> spots</div>
                  <div>Available: <strong>{stats.available}</strong> spots</div>
                  <div style={{ marginTop: '6px', color, fontWeight: 600 }}>
                    {occupancyStatus(occ)}
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>

      <Legend>
        <LegendItem color="#10b981"><div className="dot" />Available (&lt; 75%)</LegendItem>
        <LegendItem color="#f59e0b"><div className="dot" />Warning (75–90%)</LegendItem>
        <LegendItem color="#ef4444"><div className="dot" />Critical (&gt; 90%)</LegendItem>
      </Legend>

      <ZoneGrid>
        {zoneEntries.map(([zoneName, stats]) => {
          const occ   = stats.occupancy_rate || 0;
          const color = occupancyColor(occ);
          return (
            <ZoneCard key={zoneName} color={color} borderColor={color + '55'}>
              <div className="zone-name">{zoneName}</div>
              <div className="occ-value">{occ.toFixed(0)}%</div>
              <div className="occ-label">{occupancyStatus(occ)}</div>
              <div className="spots">{stats.occupied} / {stats.occupied + stats.available} spots</div>
            </ZoneCard>
          );
        })}
      </ZoneGrid>
    </Wrapper>
  );
};

export default ParkingMap;
