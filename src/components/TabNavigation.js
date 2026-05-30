import React from 'react';
import styled from 'styled-components';
import { Home, AlertCircle, BarChart3, Map, List } from 'lucide-react';

const TabBar = styled.div`
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  background: white;
  padding: 15px;
  border-radius: 10px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  flex-wrap: wrap;
`;

const Tab = styled.button`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  background: ${props => props.active ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#f0f0f0'};
  color: ${props => props.active ? 'white' : '#666'};
  cursor: pointer;
  font-size: 0.95em;
  font-weight: 500;
  transition: all 0.3s ease;
  
  svg {
    width: 18px;
    height: 18px;
  }
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
`;

const TabNavigation = ({ activeTab, setActiveTab }) => {
  const tabs = [
    { id: 'overview', label: 'Overview', icon: Home },
    { id: 'zones', label: 'Zones', icon: Map },
    { id: 'events', label: 'Latest Events', icon: List },
    { id: 'chart', label: 'Trends', icon: BarChart3 },
    { id: 'alerts', label: 'Alerts', icon: AlertCircle }
  ];

  return (
    <TabBar>
      {tabs.map(tab => {
        const Icon = tab.icon;
        return (
          <Tab
            key={tab.id}
            active={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
          >
            <Icon />
            {tab.label}
          </Tab>
        );
      })}
    </TabBar>
  );
};

export default TabNavigation;
