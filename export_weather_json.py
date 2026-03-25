import json
import time
from datetime import datetime
from pathlib import Path

import requests

API_KEY = "ae18ee9b901f65a2f173285c60225a19"
LAT = 38.895643
LON = -76.980581
REFRESH = 30
TIMEOUT = 10

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "dashboard" / "weather_data.json"

CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def get_json(url: str, params: dict) -> dict:
    response = requests.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_weather() -> dict:
    try:
        common_params = {
            "lat": LAT,
            "lon": LON,
            "appid": API_KEY,
            "units": "imperial",
        }

        current_data = get_json(CURRENT_URL, common_params)
        forecast_data = get_json(FORECAST_URL, common_params)

        forecast_list = forecast_data.get("list", [])
        if not forecast_list:
            return {"error": "No forecast list returned"}

        hourly = forecast_list[:6]

        return {
            "updated": datetime.now().strftime("%I:%M:%S %p"),
            "location": current_data.get("name", "Washington D.C."),
            "current": {
                "temp": round(current_data["main"]["temp"]),
                "desc": current_data["weather"][0]["description"],
            },
            "hourly": [
                {
                    "time": item["dt_txt"],
                    "temp": round(item["main"]["temp"]),
                    "desc": item["weather"][0]["description"],
                    "pop": round((item.get("pop", 0) or 0) * 100),
                }
                for item in hourly
            ],
        }

    except Exception as e:
        return {"error": str(e)}


def write_output(data: dict) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def main_loop() -> None:
    print("Starting weather updater...")
    print(f"Writing to: {OUTPUT_FILE}")

    while True:
        try:
            data = fetch_weather()
            write_output(data)

            if "error" in data:
                print("Weather error:", data["error"])
            else:
                print(f"Updated weather at {data['updated']}")
        except Exception as e:
            print("ERROR:", e)

        time.sleep(REFRESH)


if __name__ == "__main__":
    main_loop()