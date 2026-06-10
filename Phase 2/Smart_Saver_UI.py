import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import joblib
import requests
import numpy as np
import os
from datetime import datetime, date
import twilio
from twilio.rest import Client


# ---------------- UI ----------------
root = tk.Tk()
root.title("Smart Energy Monitor & Bill Predictor")
root.geometry("900x620")   # wider window
root.configure(bg="#1e1e1e")

# ---------------- TWILIO SETTINGS ----------------
ACCOUNT_SID = "Your_Account_SID"
AUTH_TOKEN = "Your_Account_Token"
TWILIO_PHONE = "Your_Twilio_Phone"
#If Single User
#USER_PHONES = "Your_Phone"
#If Multiple Users
USER_PHONES = [
    "Phone1",
    "Phone 2",
    "Phone 3" ]


client = Client(ACCOUNT_SID, AUTH_TOKEN)


# MAIN LAYOUT
main_frame = tk.Frame(root, bg="#1e1e1e")
main_frame.pack(fill="both", expand=True)


main_frame.columnconfigure(0, weight=1)
main_frame.columnconfigure(1, weight=1)


left_frame = tk.Frame(main_frame, bg="#1e1e1e")
right_frame = tk.Frame(main_frame, bg="#1e1e1e")

left_frame.grid(row=0, column=0, padx=20, sticky="nw")
right_frame.grid(row=0, column=1, padx=20, sticky="ne")

# ---------------- SETTINGS ----------------
ESP32_URL = "http://Your_ESP32_IP/"   # change if IP changes
MODEL_PATH = "Bill_Predictor_model.pkl"

Tariff = 3.25  # Change this to your local electricity tariff (cost per kWh)
monthly_target_value = 0
alert_sent_today = False

month_target_var = tk.StringVar()

DATA_FOLDER = "yearly_data"
os.makedirs(DATA_FOLDER, exist_ok=True)

MONTHS = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

# Load pre-trained model
model_data = joblib.load(MODEL_PATH)
model = model_data["model"]
mae = model_data["mae"]
rmse = model_data["rmse"]
r2 = model_data["r2"]

# ---------------- FILE HELPERS ----------------
def year_file(year):
    return os.path.join(DATA_FOLDER, f"data{year}.csv")

def ensure_year_file(year):
    path = year_file(year)
    if not os.path.exists(path):
        df = pd.DataFrame(columns=["Year","Month","Median_Temp","Median_Humidity","Total_kWh"])
        df.to_csv(path, index=False)

# ---------------- ESP32 SYNC ----------------
def fetch_realtime_table():
    try:
        response = requests.get(ESP32_URL, timeout=3)
        data = response.text.strip()
        parts = data.split(",")

        if len(parts) == 5:
            year, month, temp, hum, energy = parts
            for r in realtime_table.get_children():
                realtime_table.delete(r)
            realtime_table.insert("", "end",
                values=(year, month, round(float(temp),2), round(float(hum),2), round(float(energy),4)))
    except:
        for r in realtime_table.get_children():
            realtime_table.delete(r)
        realtime_table.insert("", "end", values=("Disconnected","--","--","--","--"))

    update_progress_bar()
    reset_daily_alert()
    check_energy_limit()
    root.after(5000, fetch_realtime_table)

def fetch_logged_months():
    try:
        response = requests.get(ESP32_URL + "download", timeout=5)
        if response.status_code != 200:
            raise ValueError("ESP32 not responding")

        lines = response.text.strip().splitlines()
        for line in lines:
            parts = line.split(',')
            if len(parts) != 5:
                continue

            year, month, temp, hum, kwh = parts
            year, month = int(year), int(month)
            ensure_year_file(year)
            path = year_file(year)
            df = pd.read_csv(path)
            new_row = {
                "Year": year,
                "Month": month,
                "Median_Temp": float(temp),
                "Median_Humidity": float(hum),
                "Total_kWh": float(kwh)
            }
            df = df[~((df["Year"] == year) & (df["Month"] == month))]
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(path, index=False)

        refresh_years()
        messagebox.showinfo("Sync Complete", "ESP32 logs imported successfully")
    except Exception as e:
        messagebox.showerror("Sync Error", str(e))

# ---------------- MONTH VIEW ----------------
def check_selected_month():
    try:
        if month_var.get()=="None":
            messagebox.showwarning("Error","Select month")
            return

        year=int(year_var.get())
        path=year_file(year)
        if not os.path.exists(path):
            messagebox.showwarning("No Data","No data for this year")
            return

        df=pd.read_csv(path)
        month=MONTHS.index(month_var.get())+1
        row=df[(df["Year"]==year)&(df["Month"]==month)]

        if not row.empty:
            kwh=float(row.iloc[0]["Total_kWh"])
            temp=float(row.iloc[0]["Median_Temp"])
            hum=float(row.iloc[0]["Median_Humidity"])
            bill=round(kwh * Tariff,2)
        else:
            kwh=temp=hum=bill="--"

        for r in month_result.get_children():
            month_result.delete(r)
        month_result.insert("", "end",
            values=(month_var.get(), year, f"{kwh:.4f}", f"{bill:.2f}", f"{temp:.2f}", f"{hum:.2f}"))
    except Exception as e:
        messagebox.showerror("Error",str(e))

def send_sms_warning(energy, target):
    try:
        client.messages.create(
                body=f"Warning: Energy consumption {energy:.2f} kWh exceeded your monthly target of {target:.2f} kWh.",
                from_=TWILIO_PHONE,
                to=USER_PHONES
            )
        '''
        for number in USER_PHONES:
            client.messages.create(
                body=f"Warning: Energy consumption {energy:.2f} kWh exceeded your monthly target of {target:.2f} kWh.",
                from_=TWILIO_PHONE,
                to=number
            )
            '''
    except Exception as e:
        print("SMS Error:", e)



def check_energy_limit():
    global alert_sent_today

    try:
        monthly_target = float(month_target_var.get())

        rows = realtime_table.get_children()
        if rows:
            values = realtime_table.item(rows[0])["values"]
            energy_today = float(values[4])

            if energy_today > monthly_target and not alert_sent_today:
                send_sms_warning(energy_today, monthly_target)
                alert_sent_today = True

    except:
        pass


last_day = date.today()
def reset_daily_alert():
    global alert_sent_today, last_day
    today = date.today()
    if today != last_day:
        alert_sent_today = False
        last_day = today

# ---------------- PREDICTION ----------------
def predict_bill():
    try:
        year=int(year_var.get())
        path=year_file(year)
        if not os.path.exists(path):
            messagebox.showwarning("Prediction","No yearly data")
            return

        df=pd.read_csv(path)
        if df.empty:
            messagebox.showwarning("Prediction","Empty data")
            return

        latest=df.sort_values(["Year","Month"]).iloc[-1]
        base_year=int(latest["Year"])
        base_month=int(latest["Month"])
        temp=latest["Median_Temp"]
        hum=latest["Median_Humidity"]
        prev_kwh=float(latest["Total_kWh"])

        for r in prediction_result.get_children():
            prediction_result.delete(r)

        months=[]
        if prediction_var.get()=="next_month":
            months=[(base_year+(base_month//12),(base_month%12)+1)]
        else:
            for m in range(base_month+1,13):
                months.append((base_year,m))

        for y,m in months:
            X=np.array([[y,m,temp,hum,prev_kwh]])
            pred=model.predict(X)[0]
            bill=round(pred * Tariff,2)
            prediction_result.insert("", "end",
                values=(MONTHS[m-1],y,round(pred,2),bill,round(temp,1),round(hum,1)))

    except Exception as e:
        messagebox.showerror("Prediction Error",str(e))
    
    metrics_label.config(
        text=f"Model Performance:\nR2 Score: {r2:.3f} | MAE: {mae:.2f} | RMSE: {rmse:.2f}"
    )

# ---------------- TARGET SETTINGS ----------------
def save_targets():
    global monthly_target_value
    try:
        monthly = float(month_target_var.get())

        # get current energy
        used_energy = 0
        rows = realtime_table.get_children()
        if rows:
            values = realtime_table.item(rows[0])["values"]
            used_energy = float(values[4])

        if monthly <= used_energy:
            messagebox.showerror("Invalid Entry", "Enter a Greater Value")
            return

        monthly_target_value = monthly

        messagebox.showinfo("Target Saved", f"Monthly Target: {monthly} kWh")

        update_progress_bar()

    except:
        messagebox.showerror("Error", "Enter valid number")


tk.Label(right_frame,
         text="Energy Target Settings",
         font=("Verdana",16,"bold"),
         bg="#1e1e1e",
         fg="white").pack(pady=10)

target_frame = tk.Frame(right_frame, bg="#1e1e1e")
target_frame.pack()

tk.Label(target_frame, text="Daily Target (kWh)", bg="#1e1e1e", fg="white").grid(row=0,column=0,padx=5,pady=5)
day_target_var = tk.StringVar()
tk.Entry(target_frame,textvariable=day_target_var,width=10).grid(row=0,column=1,padx=5,pady=5)

tk.Label(target_frame, text="Monthly Target (kWh)", bg="#1e1e1e", fg="white").grid(row=1,column=0,padx=5,pady=5)
tk.Entry(target_frame,textvariable=month_target_var,width=10).grid(row=1,column=1,padx=5,pady=5)

tk.Button(target_frame,text="Submit",command=save_targets,font=("Arial",10,"bold"),bg="#00cc66",fg="white",width=12).grid(row=2,column=0,columnspan=2,pady=10)

# ---------------- YEAR LIST ----------------
def refresh_years():
    years=[]
    for f in os.listdir(DATA_FOLDER):
        if f.startswith("data") and f.endswith(".csv"):
            years.append(f[4:8])
    years=sorted(years) if years else ["2026"]
    year_menu['values']=years
    year_var.set(years[-1])


def calculate_month_progress():
    try:
        year = int(year_var.get())
        path = year_file(year)
        total = 0

        # Sum past months from CSV
        if os.path.exists(path):
            df = pd.read_csv(path)
            total = df["Total_kWh"].sum()

        # Add today's real-time energy
        for row in realtime_table.get_children():
            values = realtime_table.item(row)["values"]
            if values[4] not in ("--", "Disconnected"):
                total += float(values[4])

        return total

    except:
        return 0


def update_progress_bar():
    try:
        monthly_target = float(month_target_var.get())
        used_energy = 0

        # Get the energy from the first row of realtime_table (today)
        rows = realtime_table.get_children()
        if rows:
            values = realtime_table.item(rows[0])["values"]
            used_energy = float(values[4])  # energy_today

        percent = (used_energy / monthly_target) * 100
        if percent > 100:
            percent = 100

        # Update bar value
        progress_bar["value"] = percent

        # Change color dynamically
        if percent < 70:
            style.configure("green.Horizontal.TProgressbar", foreground="green", background="green")
            progress_bar.configure(style="green.Horizontal.TProgressbar")
        elif percent <= 100:
            style.configure("yellow.Horizontal.TProgressbar", foreground="yellow", background="yellow")
            progress_bar.configure(style="yellow.Horizontal.TProgressbar")
        else:
            style.configure("red.Horizontal.TProgressbar", foreground="red", background="red")
            progress_bar.configure(style="red.Horizontal.TProgressbar")

        # Update label
        progress_label.config(
            text=f"{used_energy:.2f} / {monthly_target:.2f} kWh  ({percent:.1f}%)"
        )

        # Invalid target check
        if monthly_target < used_energy:
            messagebox.showerror("Invalid Entry", "Monthly target Exceeded!")

    except Exception as e:
        print("Progress bar update error:", e)



# ---------------- UI COMPONENTS ----------------
style=ttk.Style()
style.configure("Treeview",font=("Arial",12),rowheight=22)
style.configure("Treeview.Heading",font=("Arial",13,"bold"))

# Left Column
tk.Button(left_frame,text="Sync ESP32 Logs",command=fetch_logged_months,font=("Arial",13)).pack(pady=10)
tk.Label(left_frame,text="Select Month to View Usage",font=("Verdana",14,"bold"),bg="#1e1e1e",fg="white").pack()
frame=tk.Frame(left_frame,bg="#1e1e1e")
frame.pack(pady=5)

month_var=tk.StringVar(value="None")
year_var=tk.StringVar()
month_menu=ttk.Combobox(frame,textvariable=month_var,values=MONTHS,state="readonly",width=13)
year_menu=ttk.Combobox(frame,textvariable=year_var,state="readonly",width=8)
month_menu.pack(side="left",padx=5)
year_menu.pack(side="left",padx=5)
tk.Button(frame,text="Check Month",command=check_selected_month).pack(side="left",padx=5)

month_result=ttk.Treeview(left_frame,columns=("month","year","kwh","bill","temp","hum"),show="headings",height=1)
for c in ("month","year","kwh","bill","temp","hum"):
    month_result.heading(c,text=c.capitalize())
    month_result.column(c, width=90, anchor="center")
    
month_result.pack(pady=10)

tk.Label(left_frame,text="Real-Time Status", font=("Verdana",14,"bold"), bg="#1e1e1e", fg="white").pack(pady=10)
realtime_table = ttk.Treeview(left_frame,columns=("year","month","temp","hum","energy"),show="headings",height=1)
for c in ("year","month","temp","hum","energy"):
    realtime_table.heading(c,text=c.capitalize())
    realtime_table.column(c, width=85, anchor="center")
    
realtime_table.pack(pady=10)

tk.Label(left_frame,text="Bill Prediction",font=("Verdana",14,"bold"),bg="#1e1e1e",fg="white").pack()
prediction_var=tk.StringVar(value="next_month")
tk.Radiobutton(left_frame,text="Next Month",variable=prediction_var,value="next_month",bg="#1e1e1e",fg="white").pack()
tk.Radiobutton(left_frame,text="Remaining Year",variable=prediction_var,value="remaining_year",bg="#1e1e1e",fg="white").pack()
tk.Button(left_frame,text="Predict Bill",command=predict_bill,font=("Arial",13)).pack(pady=10)

prediction_result=ttk.Treeview(left_frame,columns=("month","year","kwh","bill","temp","hum"),show="headings",height=6)
for c in ("month","year","kwh","bill","temp","hum"):
    prediction_result.heading(c,text=c.capitalize())
    prediction_result.column(c, width=90, anchor="center")
    

prediction_result.pack(pady=10)

# Right Column
tk.Label(right_frame, text="Monthly Target Progress", font=("Verdana",16,"bold"), bg="#1e1e1e", fg="white").pack(pady=10)
progress_frame = tk.Frame(right_frame,bg="#1e1e1e")
progress_frame.pack()
progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=300, mode="determinate")
progress_bar.pack(pady=5)
progress_label = tk.Label(progress_frame, text="0%", font=("Arial",12,"bold"), bg="#1e1e1e", fg="#00ffcc")
progress_label.pack()

metrics_label = tk.Label(right_frame, text="", font=("Arial", 11, "bold"), bg="#1e1e1e", fg="#00ffcc", justify="center")
metrics_label.pack(pady=10)

# Initialize
refresh_years()
fetch_realtime_table()
root.mainloop()
