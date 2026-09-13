# AlertoPH - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Install Python Dependencies
```bash
cd alertoph
pip install -r requirements.txt
```

### Step 2: Get Your Free API Keys

#### OpenWeatherMap (Required for weather features)
1. Go to https://openweathermap.org/api
2. Click "Sign Up" (free, no credit card needed)
3. Verify your email
4. Go to API Keys section
5. Copy your API key

#### OpenRouteService (Required for routing features)
1. Go to https://openrouteservice.org/dev/#/signup
2. Sign up for free account (no credit card needed)
3. Request a token
4. Copy your API key

### Step 3: Configure Your API Keys
1. Copy the example file:
   ```bash
   copy .env.example .env
   ```

2. Edit `.env` and replace the placeholder keys:
   ```
   OPENWEATHER_API_KEY=paste_your_actual_key_here
   OPENROUTESERVICE_API_KEY=paste_your_actual_key_here
   ```

### Step 4: Run the Application
```bash
python app.py
```

You should see:
```
* Running on http://127.0.0.1:5000
```

### Step 5: Open Your Browser
Navigate to: **http://localhost:5000**

---

## 🎯 Try These Features

### Get a Safety Advisory
1. Enter "Manila" in the location search box
2. Click "Get Advisory"
3. View earthquake activity and weather conditions
4. Read the safety recommendations in English
5. Click "Switch to Filipino" to see advice in Filipino

### Plan a Safe Route
1. Click "Pick Origin" and click on the map
2. Click "Pick Destination" and click another location
3. Click "Calculate Safe Route"
4. View the route and any hazard warnings

### Use Coordinates
1. Enter latitude: `14.5995` and longitude: `120.9842` (Manila)
2. Click "Use Coordinates"
3. Get advisory for that exact location

---

## 🔧 Troubleshooting

### "Module not found" error
```bash
pip install -r requirements.txt
```

### "API key not configured" warning
- The app will still run, but features will be limited
- Add real API keys to `.env` file for full functionality
- Earthquake data works without any API key!

### Port 5000 already in use
Change the port in `app.py`:
```python
if __name__ == '__main__':
    app.run(debug=Config.DEBUG, port=5001)  # Use port 5001
```

### Map not loading
- Check your internet connection
- Leaflet.js loads from CDN
- Try refreshing the page

---

## 📱 Usage Tips

### Best Locations to Try (Philippines)
- **Manila**: `14.5995, 120.9842`
- **Cebu**: `10.3157, 123.8854`
- **Davao**: `7.1907, 125.4553`
- **Quezon City**: `14.6760, 121.0437`
- **Iloilo**: `10.7202, 122.5621`

### Understanding Severity Levels
- 🟢 **NONE/LOW**: Conditions generally safe
- 🟡 **MEDIUM**: Caution advised, monitor conditions
- 🔴 **HIGH**: Significant hazards detected, take action

### Language Toggle
- Click the language button in the header
- All safety advice updates to your chosen language
- Preference applies to current session

---

## 🧪 Testing the API Directly

### Test Advisory Endpoint
```bash
# Windows PowerShell
Invoke-RestMethod -Uri "http://localhost:5000/api/advisory?location=manila"

# Linux/Mac
curl http://localhost:5000/api/advisory?location=manila
```

### Test Hazards Endpoint
```bash
# Windows PowerShell
Invoke-RestMethod -Uri "http://localhost:5000/api/hazards"

# Linux/Mac
curl http://localhost:5000/api/hazards
```

### Test Route Endpoint
```bash
# Windows PowerShell
$body = @{
    origin = @{lat=14.5995; lng=120.9842}
    destination = @{lat=10.3157; lng=123.8854}
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5000/api/route" -Method POST -Body $body -ContentType "application/json"

# Linux/Mac
curl -X POST http://localhost:5000/api/route \
  -H "Content-Type: application/json" \
  -d '{"origin":{"lat":14.5995,"lng":120.9842},"destination":{"lat":10.3157,"lng":123.8854}}'
```

---

## 📚 Learn More

- Full documentation: See `README.md`
- Project summary: See `PROJECT_SUMMARY.md`
- Service documentation: Check docstrings in `services/` folder
- Frontend code: Check `static/js/main.js`

---

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] Python dependencies installed
- [ ] `.env` file created with API keys
- [ ] Flask app starts without errors
- [ ] Can access http://localhost:5000
- [ ] Main page loads with map
- [ ] Location search returns advisory
- [ ] Map shows Philippines region
- [ ] Language toggle switches text
- [ ] System status shows API states

---

## 🆘 Need Help?

Check the main `README.md` for:
- Detailed setup instructions
- API documentation
- Common issues
- Feature explanations
- Architecture details

---

**Enjoy using AlertoPH! Stay safe! 🇵🇭**