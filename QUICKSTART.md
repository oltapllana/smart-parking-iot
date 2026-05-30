# 🅿️ Smart Parking IoT - Quick Start Guide

## ⚡ 5-Minute Setup

### 1️⃣ One-Time Setup (2 minutes)
```bash
setup.bat
```
This installs all dependencies. **Do this once only.**

### 2️⃣ Start the API Server (Terminal 1)
```bash
start_api.bat
```
You'll see:
```
🚀 Starting Smart Parking API Server
📍 Server running on http://localhost:5000
```

### 3️⃣ Start the Dashboard (Terminal 2)
```bash
start_dashboard.bat
```
Wait for the browser to open at http://localhost:3000

### ✅ You're Done!
The dashboard is now live with:
- ✓ Real-time parking lot status
- ✓ AI availability predictions
- ✓ Zone occupancy tracking
- ✓ Alert management
- ✓ Occupancy trends

---

## 📱 Dashboard Features

### 🏠 Overview Tab
- **Quick Statistics**: Total, occupied, and available spots
- **Occupancy Bar**: Visual capacity indicator
- **Predictions**: AI-powered availability forecast
- **Recommendations**: Smart zone suggestions

### 🗺️ Zones Tab
- **Zone Cards**: Real-time status for each zone
- **Comparison Chart**: Visual zone performance
- **Availability**: Quick spot availability per zone

### 📈 Trends Tab
- **Line Chart**: Occupancy over time
- **Multiple Metrics**: Rates, occupied, and available spots
- **Patterns**: See daily parking patterns

### 🚨 Alerts Tab
- **Real-time Alerts**: Occupancy warnings
- **Severity Levels**: Critical (🔴), Warning (🟡), Info (🔵)
- **Smart Triggers**:
  - 🔴 Lot full (90%+)
  - 🟡 Near capacity (75%+)
  - 📈 Demand spike detected
  - 🚗 Zone full alerts

---

## 🔌 Manual API Testing

Once the API is running, test endpoints in your browser or terminal:

### Check System Health
```
http://localhost:5000/api/health
```

### Get Parking Status
```
http://localhost:5000/api/parking/status
```

### Get Availability Prediction
```
http://localhost:5000/api/parking/availability
```

### Get All Zones Info
```
http://localhost:5000/api/parking/zones
```

### Get Active Alerts
```
http://localhost:5000/api/parking/alerts
```

### Get Occupancy History
```
http://localhost:5000/api/parking/history?limit=50
```

---

## ⚙️ Configuration

### Change Alert Thresholds
Edit `parking_alert_engine.py`:
```python
alert_engine = ParkingAlertEngine(
    warning_threshold=75,      # Alert at 75% occupancy
    critical_threshold=90      # Critical at 90% occupancy
)
```

### Change Parking Lot Size
Edit `parking_simulator.py`:
```python
parking_lot = ParkingLot(
    'LOT-001',
    zones=4,              # Number of zones
    levels=3,             # Levels per zone
    spots_per_level=30    # Spots per level
)
# Total spots = 4 × 3 × 30 = 360
```

### Adjust Simulation Speed
In `parking_api_endpoints.py`:
```python
parking_simulator.start_simulation(interval=0.5)  # Change interval in seconds
```

---

## 🆘 Common Issues

### ❌ "Python is not installed"
**Solution**: Install Python 3.8+ from https://www.python.org
- ✅ Check "Add Python to PATH"
- ✅ Restart your computer after installation

### ❌ "Node.js not found"
**Solution**: Install Node.js from https://nodejs.org/
- ✅ Use LTS (Long Term Support) version

### ❌ "Port 5000 already in use"
**Solution**: 
- Find and close other programs using port 5000
- Or edit port in `parking_api_endpoints.py`:
  ```python
  app.run(host='0.0.0.0', port=5001, debug=True)  # Use 5001
  ```
- Update proxy in `package.json`:
  ```json
  "proxy": "http://localhost:5001"
  ```

### ❌ "Can't connect to API from Dashboard"
**Solution**:
- Ensure API server is running on http://localhost:5000
- Check: http://localhost:5000/api/health
- Refresh dashboard (Ctrl+Shift+R for hard refresh)

### ❌ "Dashboard won't start"
**Solution**:
- Run `npm install` again
- Delete `node_modules` folder and run `npm install`
- Try `npm start` directly

---

## 📊 Real-World Scenario

### Peak Hour (8:00 AM - 9:00 AM)
- Occupancy: 85%
- Alert: 🟡 WARNING - Near capacity
- Recommendation: Try Zone-3 or Zone-4
- Prediction: Will reach 90% in 15 minutes

### Mid-Day (12:00 PM)
- Occupancy: 72%
- Status: 🟢 Moderate availability
- Available spots: 100+
- Prediction: Stable demand

### Evening (6:00 PM - 7:00 PM)
- Occupancy: 88%
- Alert: 🟡 Multiple zones full
- Recommendation: Few spots available in Zone-2
- Prediction: Critical in 10 minutes

---

## 🎯 Next Steps

1. **Monitor Your System**: Watch real-time occupancy changes
2. **Test API**: Call endpoints to integrate with other systems
3. **Customize**: Adjust thresholds and lot configuration
4. **Expand**: Add payment system, reservations, or user accounts
5. **Deploy**: Run on a server for 24/7 monitoring

---

## 📞 Need Help?

1. **Check the API**: http://localhost:5000
2. **Review README**: Read the full README.md for detailed info
3. **Check Terminal**: Look for error messages in the terminal
4. **Verify Prerequisites**: Make sure Python 3.8+ and Node.js are installed

---

**Enjoy your Smart Parking System! 🅿️**
