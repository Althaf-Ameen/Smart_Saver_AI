#include <WiFi.h>
#include <WebServer.h>
#include <time.h>
#include <DHT.h>
#include <SPIFFS.h>
#include <ZMPT101B.h>
#include <Preferences.h>
Preferences preferences;

// ---------------- WIFI ----------------
const char* ssid = "Wifi_Named";
const char* password = "Wifi_Password";

// -------- STATIC IP CONFIG --------
// Change these to match your home network
IPAddress local_IP(10, 52, 74, 93); 
IPAddress gateway(10, 52, 74, 1);     
IPAddress subnet(255, 255, 255, 0);
IPAddress primaryDNS(8, 8, 8, 8);
IPAddress secondaryDNS(8, 8, 4, 4);

// ---------------- TIME ----------------
const long gmtOffset_sec = 19800;   // IST
const int daylightOffset_sec = 0;

// ---------------- SERVER ----------------
WebServer server(80);

// ---------------- SENSORS ----------------
#define DHTPIN 27
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

#define VOLTAGE_PIN 32
ZMPT101B voltageSensor(VOLTAGE_PIN, 50.0);

#define CURRENT_PIN 34
int mVperAmp = 100; // ACS712 20A

// ---------------- DAILY ACCUMULATORS ----------------
float energy_today = 0;
float temp_sum = 0;
float hum_sum = 0;
int reading_count = 0;

unsigned long lastSample = 0;
unsigned long lastDay = 0;


// virtual month (1–12)
int virtualMonth = 1;

// ---------------- ENERGY CALC ----------------
float readEnergy(float &voltageOut, float &currentOut)
{
  voltageOut = voltageSensor.getRmsVoltage();

  const int samples = 600;   // number of ADC samples
  float sum = 0;

  for (int i = 0; i < samples; i++)
  {
    int adc = analogRead(CURRENT_PIN);
    float voltageADC = adc * 3.3 / 4095.0;

    float centered = voltageADC - 2.445;  // center for 5V powered ACS712
    sum += centered * centered;

    delayMicroseconds(200);  // sampling delay
  }

  float rmsVoltage = sqrt(sum / samples);

  currentOut = rmsVoltage / 0.185;  // 5A version = 185mV per Amp

  if (currentOut < 0.12) currentOut = 0;  // noise filter

  float power = voltageOut * currentOut;

  return power / 3600000.0;  // convert to kWh per second
}

// ---------------- SAVE DAY AS MONTH ----------------
void saveDay()
{
  if (reading_count == 0) return;
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) return;

  int year = timeinfo.tm_year + 1900;

  float avgTemp = temp_sum / reading_count;
  float avgHum  = hum_sum / reading_count;

  File file = SPIFFS.open("/dataset.csv", FILE_APPEND);

  if (file)
  {
    file.printf("%d,%d,%.2f,%.2f,%.4f\n",
                year, virtualMonth,
                avgTemp, avgHum, energy_today);
    file.close();
  }

  Serial.println("Day stored as Month " + String(virtualMonth));

  // next month (cycle 1-12)
  virtualMonth++;
  if (virtualMonth > 12) virtualMonth = 1;

  // reset counters
  energy_today = 0;
  temp_sum = 0;
  hum_sum = 0;
  reading_count = 0;

  preferences.putFloat("energy", energy_today);
  preferences.putFloat("temp", temp_sum);
  preferences.putFloat("hum", hum_sum);
  preferences.putInt("count", reading_count);
  preferences.putInt("month", virtualMonth);
}

// ---------------- DOWNLOAD ENDPOINT ----------------
void handleDownload()
{
  if (!SPIFFS.exists("/dataset.csv"))
  {
    server.send(200, "text/plain", "No Data");
    return;
  }

  File file = SPIFFS.open("/dataset.csv");
  server.streamFile(file, "text/plain");
  file.close();
}

// ---------------- REALTIME ENDPOINT ----------------
void handleRealtime()
{
  int year = 2026;  // fixed year (or you can change manually)

  float avgTemp = (reading_count > 0) ? temp_sum / reading_count : 0;
  float avgHum  = (reading_count > 0) ? hum_sum / reading_count : 0;

  String data = String(year) + "," +
                String(virtualMonth) + "," +
                String(avgTemp, 2) + "," +
                String(avgHum, 2) + "," +
                String(energy_today, 4);

  server.send(200, "text/plain", data);
}


// ---------------- SETUP ----------------
void setup()
{
  Serial.begin(115200);

  dht.begin();

  delay (2000);

  analogReadResolution(12);
  voltageSensor.setSensitivity(500.0f);

  if (!SPIFFS.begin(true))
  {
    Serial.println("SPIFFS Failed");
    return;
  }

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");

  int attempts = 0;

  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
    attempts++;

    if (attempts > 30) {
      Serial.println("\n❌ Failed to connect!");
      return;
    }
  }

  Serial.println("\n✅ Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  server.on("/", handleRealtime);     
  server.on("/download", handleDownload);
  configTime(gmtOffset_sec, daylightOffset_sec, "pool.ntp.org");
  server.begin();




  preferences.begin("energyData", false);

  // Load saved values (if they exist)
  energy_today  = preferences.getFloat("energy", 0.0);
  temp_sum      = preferences.getFloat("temp", 0.0);
  hum_sum       = preferences.getFloat("hum", 0.0);
  reading_count = preferences.getInt("count", 0);
  virtualMonth  = preferences.getInt("month", 1);

  Serial.println("Recovered Values:");

  Serial.print("Energy Recorded: ");
  Serial.println(energy_today);

  Serial.print("Temperature Sum: ");
  Serial.println(temp_sum);

  Serial.print("Humidity Sum: ");
  Serial.println(hum_sum);
  
  Serial.print("Reading Counts: ");
  Serial.println(reading_count);

  Serial.print("Virtual Month: ");
  Serial.println(virtualMonth);

}

// ---------------- LOOP ----------------
void loop()
{
  server.handleClient();

  // sample every 5 seconds
  if (millis() - lastSample > 5000)
  {
    lastSample = millis();

    float t = dht.readTemperature();
    float h = dht.readHumidity();

    if (!isnan(t) && !isnan(h))
    {
      temp_sum += t;
      hum_sum += h;
      reading_count++;
      // 24 hours completed (5 sec interval = 17280 samples)
      if (reading_count >= 17280)
      {
        saveDay();
      }
    }

    float voltage, current;
    float energyIncrement = readEnergy(voltage, current);

    energy_today += energyIncrement;

    Serial.printf("Temp: %.2f C | Hum: %.2f %% | Voltage: %.2f V | Current: %.4f A | Energy: %.8f kWh | Samples: %d\n",t, h, voltage, current, energy_today, reading_count);

    preferences.putFloat("energy", energy_today);
    preferences.putFloat("temp", temp_sum);
    preferences.putFloat("hum", hum_sum);
    preferences.putInt("count", reading_count);
    preferences.putInt("month", virtualMonth);

  }

  // EXACT 24 HOURS
  if (millis() - lastDay >= 86400000)
  {
    saveDay();
    lastDay = millis ();
  }
}