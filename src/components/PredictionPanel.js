import React from 'react';
import styled from 'styled-components';
import { TrendingUp, TrendingDown, Minus, ArrowRight } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, CartesianGrid,
} from 'recharts';

const Container = styled.div`
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-radius: 12px;
  padding: 25px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(148, 163, 184, 0.15);
`;

const Subtitle = styled.p`
  color: #94a3b8;
  font-size: 0.85em;
  margin: 4px 0 14px 0;
  line-height: 1.4;
`;

// Context badges: weather + special event feeding the model
const Context = styled.div`
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
`;

const Badge = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  background: ${p => p.$bg || 'rgba(148, 163, 184, 0.15)'};
  color: ${p => p.$fg || '#cbd5e1'};
  border: 1px solid ${p => p.$border || 'rgba(148, 163, 184, 0.25)'};
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.82em;
  font-weight: 600;
  small { font-weight: 400; opacity: 0.8; }
`;

// "Now -> in 30 min" forecast strip
const Forecast = styled.div`
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 10px;
  background: rgba(148, 163, 184, 0.08);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 16px;
`;

const ForecastCell = styled.div`
  text-align: center;
  small {
    display: block;
    color: #94a3b8;
    font-size: 0.72em;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
  }
  strong {
    font-size: 1.9em;
    color: #e2e8f0;
  }
`;

const Arrow = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  color: ${p => p.$dir === 'increasing' ? '#f5576c' : p.$dir === 'decreasing' ? '#43e97b' : '#94a3b8'};
  font-size: 0.8em;
  font-weight: bold;
  svg { width: 22px; height: 22px; }
`;

const ChartBox = styled.div`
  background: rgba(148, 163, 184, 0.06);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 10px;
  padding: 14px 10px 6px 0;
  margin-bottom: 16px;
`;

const ChartTitle = styled.div`
  color: #94a3b8;
  font-size: 0.78em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 6px 16px;
`;

const Legend = styled.div`
  display: flex;
  gap: 16px;
  margin: 2px 0 0 16px;
  font-size: 0.72em;
  color: #94a3b8;
  span { display: flex; align-items: center; gap: 5px; }
  i { width: 14px; height: 3px; border-radius: 2px; display: inline-block; }
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
  margin-bottom: 20px;
`;

const StatCard = styled.div`
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 18px;
  border-radius: 8px;
  text-align: center;

  &.warning { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
  &.success { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
  &.danger  { background: linear-gradient(135deg, #ee0979 0%, #ff6a00 100%); }
`;

const StatLabel = styled.div`
  font-size: 0.85em;
  opacity: 0.9;
  margin-bottom: 8px;
  text-transform: uppercase;
`;

const StatValue = styled.div`
  font-size: 2em;
  font-weight: bold;
`;

// Class probability bars
const Probs = styled.div`
  margin: 18px 0 6px 0;
`;

const ProbHeader = styled.div`
  color: #94a3b8;
  font-size: 0.78em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
`;

const ProbRow = styled.div`
  display: grid;
  grid-template-columns: 70px 1fr 44px;
  align-items: center;
  gap: 10px;
  margin-bottom: 7px;
  font-size: 0.85em;
  color: #cbd5e1;
`;

const BarTrack = styled.div`
  background: rgba(148, 163, 184, 0.15);
  border-radius: 6px;
  height: 12px;
  overflow: hidden;
`;

const BarFill = styled.div`
  height: 100%;
  width: ${p => p.$pct}%;
  background: ${p => p.$color};
  border-radius: 6px;
  transition: width 0.5s ease;
`;

const RecommendationBox = styled.div`
  background: rgba(148, 163, 184, 0.2);
  border-left: 4px solid #667eea;
  padding: 15px;
  border-radius: 5px;
  margin-top: 15px;

  strong { color: #818cf8; }
  p { margin: 6px 0 0 0; color: #e2e8f0; }
`;

const ModelFooter = styled.div`
  margin-top: 14px;
  font-size: 0.78em;
  color: #64748b;
  border-top: 1px solid rgba(148, 163, 184, 0.12);
  padding-top: 10px;
  strong { color: #94a3b8; }
`;

const CLASS_META = {
  HIGH:   { color: '#43e97b', label: 'Plenty of spots' },
  MEDIUM: { color: '#667eea', label: 'Some searching' },
  LOW:    { color: '#f5576c', label: 'Hard to find' },
  FULL:   { color: '#ee0979', label: 'Lot full' },
};

const availabilityClass = (a) =>
  a === 'HIGH' ? 'success' : a === 'LOW' ? 'warning' : a === 'FULL' ? 'danger' : '';

const WEATHER_META = {
  clear: { icon: '☀️', label: 'Clear', note: 'normal demand' },
  rain:  { icon: '🌧️', label: 'Rain', note: '+demand' },
  snow:  { icon: '❄️', label: 'Snow', note: '++demand' },
};

const PredictionPanel = ({ prediction, demand, modelInfo, history: occHistory, weather, specialEvent }) => {
  if (!prediction) {
    return <Container>Loading predictions...</Container>;
  }

  const wx = WEATHER_META[(weather || 'clear').toLowerCase()] || WEATHER_META.clear;

  const now = prediction.occupancy_rate ?? 0;
  const future = demand?.predicted_occupancy_rate;
  const dir = demand?.trend_direction || 'stable';
  const trend = demand?.trend ?? 0;
  const horizon = demand?.time_horizon || 30;

  const probs = prediction.class_probabilities || {};
  const order = ['HIGH', 'MEDIUM', 'LOW', 'FULL'];

  // Build the trajectory: recent observed occupancy (solid) -> forecast (dashed)
  const past = (occHistory || [])
    .slice(-12)
    .map(h => (typeof h === 'number' ? h : h.occupancy_rate))
    .filter(v => v != null);
  const chartData = past.map((v, i) => ({ t: `-${past.length - i}`, past: Math.round(v) }));
  if (chartData.length > 0) {
    // bridge point so the dashed forecast line starts where history ends
    chartData[chartData.length - 1].forecast = chartData[chartData.length - 1].past;
    if (future != null) {
      chartData.push({ t: `+${horizon}m`, forecast: Math.round(future) });
    }
  }

  return (
    <Container>
      <h3>🔮 Predictions</h3>
      <Subtitle>
        The AI forecasts <strong>how full the lot will be in ~{horizon} min</strong> and
        whether you'll find a spot — using current occupancy, its recent trend,
        time of day, <strong>weather</strong> and <strong>special events</strong>.
      </Subtitle>

      {/* Live context that the model factors in */}
      <Context>
        <Badge>
          <span style={{ fontSize: '1.15em' }}>{wx.icon}</span>
          {wx.label} <small>({wx.note})</small>
        </Badge>
        {specialEvent ? (
          <Badge $bg="rgba(245, 87, 108, 0.18)" $fg="#fda4af" $border="rgba(245, 87, 108, 0.4)">
            🎉 Special event <small>(demand spike)</small>
          </Badge>
        ) : (
          <Badge>📅 No event</Badge>
        )}
      </Context>

      {/* What we predict: occupancy now -> in 30 min */}
      <Forecast>
        <ForecastCell>
          <small>Occupancy now</small>
          <strong>{now.toFixed(1)}%</strong>
        </ForecastCell>
        <Arrow $dir={dir}>
          {dir === 'increasing' ? <TrendingUp /> : dir === 'decreasing' ? <TrendingDown /> : <ArrowRight />}
          <span>{trend > 0 ? '+' : ''}{trend.toFixed(1)}%</span>
        </Arrow>
        <ForecastCell>
          <small>Forecast (+{horizon}m)</small>
          <strong>{future != null ? `${future.toFixed(1)}%` : '—'}</strong>
        </ForecastCell>
      </Forecast>

      {/* Trajectory: where occupancy has been -> where it's headed */}
      {chartData.length > 1 && (
        <ChartBox>
          <ChartTitle>Occupancy trajectory → forecast</ChartTitle>
          <ResponsiveContainer width="100%" height={130}>
            <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
              <XAxis dataKey="t" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 11 }} width={32} unit="%" />
              <Tooltip
                contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0' }}
                formatter={(v, name) => [`${v}%`, name === 'past' ? 'Observed' : 'Forecast']}
              />
              <ReferenceLine x="0" stroke="#475569" strokeDasharray="2 2" label={{ value: 'now', fill: '#94a3b8', fontSize: 10, position: 'top' }} />
              <Line type="monotone" dataKey="past" stroke="#667eea" strokeWidth={2.5} dot={false} isAnimationActive={false} connectNulls />
              <Line type="monotone" dataKey="forecast" stroke="#f5576c" strokeWidth={2.5} strokeDasharray="5 4" dot={{ r: 3, fill: '#f5576c' }} isAnimationActive={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
          <Legend>
            <span><i style={{ background: '#667eea' }} /> Observed (past)</span>
            <span><i style={{ background: '#f5576c' }} /> AI forecast (+{horizon}m)</span>
          </Legend>
        </ChartBox>
      )}

      <Grid>
        <StatCard className={availabilityClass(prediction.availability)}>
          <StatLabel>Will I find a spot?</StatLabel>
          <StatValue>{prediction.availability}</StatValue>
          <div style={{ fontSize: '0.85em', marginTop: '8px' }}>
            Confidence: {(prediction.confidence * 100).toFixed(0)}%
          </div>
        </StatCard>

        <StatCard>
          <StatLabel>Predicted demand</StatLabel>
          <StatValue>{demand?.demand_level || '—'}</StatValue>
          <div style={{ fontSize: '0.85em', marginTop: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
            {dir === 'increasing' ? <TrendingUp size={16} /> : dir === 'decreasing' ? <TrendingDown size={16} /> : <Minus size={16} />}
            {dir}
          </div>
        </StatCard>
      </Grid>

      {/* Probability breakdown so it's clear the model chooses among 4 classes */}
      {Object.keys(probs).length > 0 && (
        <Probs>
          <ProbHeader>Availability probability (next {horizon} min)</ProbHeader>
          {order.filter(c => c in probs).map(c => {
            const pct = (probs[c] || 0) * 100;
            const meta = CLASS_META[c];
            return (
              <ProbRow key={c}>
                <span style={{ color: meta.color, fontWeight: 'bold' }}>{c}</span>
                <BarTrack><BarFill $pct={pct} $color={meta.color} /></BarTrack>
                <span style={{ textAlign: 'right' }}>{pct.toFixed(0)}%</span>
              </ProbRow>
            );
          })}
        </Probs>
      )}

      <RecommendationBox>
        <strong>💡 Recommendation:</strong>
        <p>{prediction.recommendation}</p>
      </RecommendationBox>

      {prediction.model && (
        <ModelFooter>
          🤖 Model: <strong>{prediction.model}</strong>
          {modelInfo?.classifier_accuracy != null && (
            <> · accuracy <strong>{(modelInfo.classifier_accuracy * 100).toFixed(0)}%</strong></>
          )}
          {' '}· trained on the IoT data the pipeline collects
        </ModelFooter>
      )}
    </Container>
  );
};

export default PredictionPanel;
