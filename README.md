# SmartSaver - Smart Electricity Monitoring and Forecasting System

A IoT + Machine Learning based electricity monitoring and bill forecasting 
system designed for middle-class households.

Built as a Final Year B.Tech Project at Ilahia College of Engineering and 
Technology, under APJ Abdul Kalam Technological University, Kerala.

---

## Project Structure

```
SmartSaver/
│
├── Phase 1/
│   └── sketch_sep26a/
│       └── sketch_sep26a.ino
│
├── Phase 2/
│   ├── sketch_feb16a/
│   │   └── sketch_feb16a.ino
│   ├── Smart_Saver_UI.py
│   └── Train_Model.py
│
├── .gitignore
├── README.md
├── requirements.txt
└── LICENSE

```

---

## How It Works

**Phase 1 — IoT Monitoring**
- ESP32 microcontroller reads voltage, current and power data
- Data is displayed on LCD and sent to Blynk dashboard

**Phase 2 — AI Forecasting**
- ESP32 collects real-time energy and environmental data
- Desktop app built with Python and Tkinter
- Machine learning model predicts future electricity bills
- SMS alerts sent via Twilio when usage exceeds target

---

## Setup Instructions

### Python App
1. Clone this repository

2. Install dependencies:

```
pip install -r requirements.txt
```

3. Open `Smart_Saver_UI.py` and configure:
- `ACCOUNT_SID` — your Twilio Account SID
- `AUTH_TOKEN` — your Twilio Auth Token
- `TWILIO_PHONE` — your Twilio phone number
- `USER_PHONES` — recipient phone numbers
- `ESP32_URL` — your ESP32's IP address
- `Tariff` — your local electricity tariff (cost per kWh)

4. Train the model first:
```
python Train_Model.py
```

5. Place the generated `bill_predictor_model.pkl` in the same folder as `Smart_Saver_UI.py`

6. Update `MODEL_PATH` in `Smart_Saver_UI.py`:
```
   MODEL_PATH = "bill_predictor_model.pkl"
```

7. Run the app:
```
python Smart_Saver_UI.py
```

### ESP32 Firmware
1. Open `sketch_feb16a.ino` in Arduino IDE

2. Configure:
- `ssid` — your WiFi name
- `password` — your WiFi password
- Static IP settings to match your network

3. Flash to your ESP32

---

## Hardware Required
- ESP32 Microcontroller
- ZMPT101B Voltage Sensor
- ACS712 Current Sensor
- DHT22 Temperature and Humidity Sensor

---

## Tech Stack
- **Hardware:** ESP32, ZMPT101B, ACS712, DHT22
- **Frontend:** Python, Tkinter
- **ML Model:** ExtraTreesRegressor (scikit-learn)
- **Alerts:** Twilio SMS API
- **Data:** CSV files, joblib

---

## Author
Althaf Ameen Haneefa
B.Tech — Artificial Intelligence and Data Science
Ilahia College of Engineering and Technology, Muvattupuzha
2026

---

## License
This project is licensed under the MIT License.