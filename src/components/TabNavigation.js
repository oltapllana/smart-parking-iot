import React from 'react';
import styled from 'styled-components';
import { Home, AlertCircle, BarChart3, Map, List, Settings } from 'lucide-react';

const TabBar = styled.div`
  display: flex;
  gap: 12px;
  margin-bottom: 25px;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  flex-wrap: wrap;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
`;

const Tab = styled.button`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border: none;
  border-radius: 8px;
  background: ${props => props.active 
    ? 'linear-gradient(135deg, #3b82f6 0%, #1e40af 100%)' 
    : 'rgba(148, 163, 184, 0.1)'};
  color: ${props => props.active ? '#ffffff' : '#cbd5e1'};
  cursor: pointer;
  font-size: 0.95em;
  font-weight: 500;
  transition: all 0.3s ease;
  border: 1px solid ${props => props.active 
    ? 'rgba(59, 130, 246, 0.5)' 
    : 'transparent'};
  
  svg {
    width: 18px;
    height: 18px;
  }
  
  &:hover {
    transform: translateY(-2px);
    background: ${props => props.active 
      ? 'linear-gradient(135deg, #3b82f6 0%, #1e40af 100%)' 
      : 'rgba(148, 163, 184, 0.2)'};
    box-shadow: 0 4px 15px ${props => props.active 
      ? 'rgba(59, 130, 246, 0.3)' 
      : 'rgba(0, 0, 0, 0.2)'};
  }
`;

const TabNavigation = ({ activeTab, setActiveTab }) => {
  const tabs = [
    { id: 'overview', label: 'Overview', icon: Home },
    { id: 'zones', label: 'Zones', icon: Map },
    { id: 'chart', label: 'Trends', icon: BarChart3 },
    { id: 'events', label: 'Events', icon: List },
    { id: 'alerts', label: 'Alerts', icon: AlertCircle },
    { id: 'system', label: 'System', icon: Settings }
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
