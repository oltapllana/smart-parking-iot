import React, { useState, useEffect } from 'react';
import axios from 'axios';
import styled from 'styled-components';
import { Activity, AlertCircle, TrendingUp, MapPin } from 'lucide-react';
import ParkingOverview from './components/ParkingOverview';
import ZoneStatus from './components/ZoneStatus';
import OccupancyChart from './components/OccupancyChart';
import AlertPanel from './components/AlertPanel';
import PredictionPanel from './components/PredictionPanel';
import TabNavigation from './components/TabNavigation';
import EventsPanel from './components/EventsPanel';

const AppContainer = styled.div`
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  padding: 20px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
`;

const Header = styled.header`
  background: rgba(255, 255, 255, 0.1);
  color: white;
  padding: 30px;
  border-radius: 10px;
  margin-bottom: 30px;
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
`;

const Title = styled.h1`
  margin: 0;
  font-size: 2.5em;
  display: flex;
  align-items: center;
  gap: 15px;
  
  svg {
    width: 40px;
    height: 40px;
  }
`;

const Subtitle = styled.p`
  margin: 10px 0 0 0;
  font-size: 1.1em;
  opacity: 0.9;
`;

const MainGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
`;

const Card = styled.div`
  background: white;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
  
  &:hover {
    transform: translateY(-5px);
  }
`;

const ErrorMessage = styled.div`
  background: #fee;
  border-left: 4px solid #f00;
  color: #c00;
  padding: 15px;
  border-radius: 5px;
  margin-bottom: 20px;
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

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchAllData = async () => {
    try {
      setError(null);
      const [statusRes, alertsRes, predictRes, historyRes, eventsRes] = await Promise.all([
        axios.get('/api/parking/status'),
        axios.get('/api/parking/alerts'),
        axios.get('/api/parking/availability'),
        axios.get('/api/parking/history?limit=50'),
        axios.get('/api/parking/events?limit=50')
      ]);

      setParkingData(statusRes.data);
      setAlerts(alertsRes.data.alerts || []);
      setPredictions(predictRes.data);
      setOccupancyHistory(historyRes.data.history || []);
      setEvents(eventsRes.data.events || eventsRes.data || []);
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
          <Title>🅿️ Smart Parking IoT System</Title>
          <Subtitle>Loading...</Subtitle>
        </Header>
      </AppContainer>
    );
  }

  return (
    <AppContainer>
      <Header>
        <Title>
          <Activity size={40} />
          Smart Parking IoT System
        </Title>
        <Subtitle>Real-time parking lot monitoring and predictions</Subtitle>
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
                <p>{alerts[0].message}</p>
              </Card>
            )}
          </MainGrid>
        </>
      )}

      {activeTab === 'zones' && parkingData && (
        <MainGrid>
          <ZoneStatus zones={parkingData.lot_data.zone_statistics} />
        </MainGrid>
      )}

      {activeTab === 'alerts' && (
        <Card>
          <AlertPanel alerts={alerts} />
        </Card>
      )}

      {activeTab === 'chart' && (
        <Card>
          <OccupancyChart history={occupancyHistory} />
        </Card>
      )}

      {activeTab === 'events' && (
        <Card>
          <h3>📋 Latest Events</h3>
          <EventsPanel events={events} />
        </Card>
      )}
    </AppContainer>
  );
}

export default App;
