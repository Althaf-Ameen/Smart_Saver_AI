import pandas as pd
import numpy as np
import os
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

DATA_FOLDER = "yearly_data"

# LOAD DATA
all_data = []

for file in os.listdir(DATA_FOLDER):
    if file.endswith(".csv"):
        df = pd.read_csv(os.path.join(DATA_FOLDER,file))
        all_data.append(df)

if not all_data:
    print("No data found.")
    exit()

df = pd.concat(all_data, ignore_index=True)

# FEATURES
X = df[[
    "Year",
    "Month",
    "Median_Temp",
    "Median_Humidity",
    "Prev_Month_kWh"
]]

# TARGET
y = df["Total_kWh"]

# TRAIN TEST SPLIT
X_train, X_test, y_train, y_test = train_test_split(
    X,y,test_size=0.2,random_state=42
)

# MODEL
model = ExtraTreesRegressor(
    n_estimators=500,
    random_state=42
)

model.fit(X_train,y_train)

# PREDICTION
y_pred = model.predict(X_test)

# METRICS
mae = mean_absolute_error(y_test,y_pred)
mse = mean_squared_error(y_test,y_pred)
rmse = np.sqrt(mse)
r2 = r2_score(y_test,y_pred)

print("\nModel Performance")
print("MAE:",mae)
print("RMSE:",rmse)
print("R2 Score:",r2)

# SAVE MODEL
model_data = {
    "model":model,
    "mae":mae,
    "rmse":rmse,
    "r2":r2
}

joblib.dump(model_data,"bill_predictor_model.pkl")

print("\nModel saved successfully.")
