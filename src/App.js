import React, { useState, useEffect } from 'react';
import axios from 'axios';
import styled from 'styled-components';
import { Activity, AlertCircle, TrendingUp, MapPin } from 'lucide-react';
import ParkingOverview from './components/ParkingOverview';
import ParkingMap from './components/ParkingMap';
import ZoneStatus from './components/ZoneStatus';
import OccupancyChart from './components/OccupancyChart';
import AlertPanel from './components/AlertPanel';
import PredictionPanel from './components/PredictionPanel';
import TabNavigation from './components/TabNavigation';
import EventsPanel from './components/EventsPanel';
import SystemStatus from './components/SystemStatus';
import PerformancePanel from './components/PerformancePanel';

const AppContainer = styled.div`
  background: #0f172a;
  min-height: 100vh;
  padding: 20px;
  font-family: 'Inter', 'Segoe UI', sans-serif;
  color: #e2e8f0;
`;

const Header = styled.header`
  background: linear-gradient(135deg, #1e3a8a 0%, #312e81 100%);
  color: white;
  padding: 40px;
  border-radius: 15px;
  margin-bottom: 30px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3), 0 0 40px rgba(30, 58, 138, 0.3);
  border: 1px solid rgba(148, 163, 184, 0.1);
  position: relative;
  overflow: hidden;
  
  &::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -50%;
    width: 100%;
    height: 100%;
    background: radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 70%);
    pointer-events: none;
  }
`;

const HeaderContent = styled.div`
  position: relative;
  z-index: 1;
`;

const Title = styled.h1`
  margin: 0;
  font-size: 2.8em;
  display: flex;
  align-items: center;
  gap: 15px;
  font-weight: 700;
  background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  
  svg {
    width: 45px;
    height: 45px;
    color: #60a5fa;
  }
`;

const Subtitle = styled.p`
  margin: 15px 0 0 0;
  font-size: 1.1em;
  opacity: 0.85;
  font-weight: 400;
`;

const StatusBar = styled.div`
  display: flex;
  gap: 20px;
  margin-top: 20px;
  flex-wrap: wrap;
  padding-top: 20px;
  border-top: 1px solid rgba(148, 163, 184, 0.2);
`;

const StatusItem = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.95em;
  
  .status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: ${props => props.status === 'running' ? '#10b981' : '#ef4444'};
    box-shadow: 0 0 8px ${props => props.status === 'running' ? '#10b981' : '#ef4444'};
    animation: pulse 2s infinite;
  }
  
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
`;

const MainGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 25px;
  margin-bottom: 30px;
  
  @media (max-width: 1200px) {
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  }
  
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;

const Card = styled.div`
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-radius: 12px;
  padding: 25px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
  border: 1px solid rgba(148, 163, 184, 0.15);
  color: #e2e8f0;
  
  h3 {
    color: #e2e8f0;
    margin: 0 0 15px 0;
  }
  
  &:hover {
    transform: translateY(-8px);
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.15);
    border-color: rgba(148, 163, 184, 0.25);
  }
`;

const FullWidthCard = styled(Card)`
  grid-column: 1 / -1;
`;

const ChartCard = styled(FullWidthCard)`
  min-height: 400px;
`;

const ErrorMessage = styled.div`
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(220, 38, 38, 0.1) 100%);
  border-left: 4px solid #ef4444;
  color: #fca5a5;
  padding: 15px 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  border: 1px solid rgba(239, 68, 68, 0.3);
`;

const LoadingContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 20px;
`;

const Spinner = styled.div`
  width: 50px;
  height: 50px;
  border: 4px solid rgba(148, 163, 184, 0.2);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`;

function App() {
  const [parkingData, setParkingData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [predictions, setPredictions] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [occupancyHistory, setOccupancyHistory] = useState([]);
  const [systemMetrics, setSystemMetrics] = useState({});
  const [performance, setPerformance] = useState(null);
  const [windows, setWindows] = useState([]);

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchAllData = async () => {
    try {
      setError(null);
      const [statusRes, alertsRes, predictRes, historyRes, eventsRes, perfRes, windowsRes] = await Promise.all([
        axios.get('/api/parking/status'),
        axios.get('/api/parking/alerts'),
        axios.get('/api/parking/availability'),
        axios.get('/api/parking/history?limit=50'),
        axios.get('/api/parking/events?limit=50'),
        axios.get('/api/parking/performance'),
        axios.get('/api/parking/windows?limit=10')
      ]);

      setParkingData(statusRes.data);
      setAlerts(alertsRes.data.alerts || []);
      setPredictions(predictRes.data);
      setOccupancyHistory(historyRes.data.history || []);
      setEvents(eventsRes.data.events || eventsRes.data || []);
      setPerformance(perfRes.data);
      setWindows(windowsRes.data.windows || []);

      // Real pipeline metrics from the performance monitor
      const perf = perfRes.data || {};
      setSystemMetrics({
        kafka_messages: perf.counters?.kafka_messages || 0,
        spark_processed: perf.counters?.spark_processed || 0,
        cassandra_events: perf.counters?.cassandra_events || 0,
        api_health: perf.health?.data_quality_pct || 100,
        processing_latency: perf.latency?.end_to_end_ms || 0,
        throughput: perf.throughput?.spark_eps || 0,
        latency: perf.latency || {},
      });

      setLoading(false);
    } catch (err) {
      setError('Failed to fetch parking data. Please ensure the API server is running.');
      console.error('Error fetching data:', err);
    }
  };

  if (loading && !parkingData) {
    return (
      <AppContainer>
        <Header>
          <HeaderContent>
            <Title>🅿️ Smart Parking IoT System</Title>
            <Subtitle>Loading...</Subtitle>
          </HeaderContent>
        </Header>
        <LoadingContainer>
          <Spinner />
          <p style={{ fontSize: '1.1em', opacity: 0.7 }}>Initializing IoT pipeline...</p>
        </LoadingContainer>
      </AppContainer>
    );
  }

  return (
    <AppContainer>
      <Header>
        <HeaderContent>
          <Title>
            <Activity size={45} />
            Smart Parking IoT System
          </Title>
          <Subtitle>Real-time IoT monitoring with Kafka → Spark → Cassandra pipeline</Subtitle>
          <StatusBar>
            <StatusItem status="running">
              <div className="status-dot"></div>
              <span>Sensor Simulator: Active</span>
            </StatusItem>
            <StatusItem status="running">
              <div className="status-dot"></div>
              <span>Kafka Stream: Connected</span>
            </StatusItem>
            <StatusItem status="running">
              <div className="status-dot"></div>
              <span>Spark Streaming: Processing</span>
            </StatusItem>
            <StatusItem status="running">
              <div className="status-dot"></div>
              <span>Cassandra DB: Online</span>
            </StatusItem>
          </StatusBar>
        </HeaderContent>
      </Header>

      {error && <ErrorMessage>⚠️ {error}</ErrorMessage>}

      <TabNavigation activeTab={activeTab} setActiveTab={setActiveTab} />

      {activeTab === 'overview' && (
        <>
          <MainGrid>
            {parkingData && <ParkingOverview data={parkingData.lot_data} />}
            {predictions && <PredictionPanel prediction={predictions} />}
            {alerts.length > 0 && (
              <Card>
                <h3>🚨 Active Alerts ({alerts.length})</h3>
                <div style={{ marginTop: '15px', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', borderLeft: '3px solid #ef4444' }}>
                  <p style={{ margin: '0 0 8px 0', fontSize: '0.95em' }}><strong>{alerts[0].alert_type}</strong></p>
                  <p style={{ margin: 0, opacity: 0.8, fontSize: '0.9em' }}>{alerts[0].message}</p>
                  <p style={{ margin: '8px 0 0 0', fontSize: '0.85em', opacity: 0.6 }}>{new Date(alerts[0].timestamp).toLocaleTimeString()}</p>
                </div>
              </Card>
            )}
          </MainGrid>
          
          {events.length > 0 && (
            <FullWidthCard>
              <h3 style={{ marginTop: 0 }}>📋 Recent Events</h3>
              <EventsPanel events={events} />
            </FullWidthCard>
          )}
        </>
      )}

      {activeTab === 'map' && parkingData && (
        <FullWidthCard>
          <ParkingMap zones={parkingData.lot_data.zone_statistics} />
        </FullWidthCard>
      )}

      {activeTab === 'zones' && parkingData && (
        <MainGrid>
          <FullWidthCard>
            <ZoneStatus zones={parkingData.lot_data.zone_statistics} />
          </FullWidthCard>
        </MainGrid>
      )}

      {activeTab === 'alerts' && (
        <FullWidthCard>
          <AlertPanel alerts={alerts} />
        </FullWidthCard>
      )}

      {activeTab === 'chart' && (
        <ChartCard>
          <OccupancyChart history={occupancyHistory} />
        </ChartCard>
      )}

      {activeTab === 'events' && (
        <FullWidthCard>
          <h3 style={{ marginTop: 0 }}>📋 Event Log</h3>
          <EventsPanel events={events} />
        </FullWidthCard>
      )}

      {activeTab === 'performance' && (
        <FullWidthCard>
          <PerformancePanel performance={performance} windows={windows} />
        </FullWidthCard>
      )}

      {activeTab === 'system' && (
        <FullWidthCard>
          <SystemStatus systemMetrics={systemMetrics} />
        </FullWidthCard>
      )}
    </AppContainer>
  );
}

export default App;
