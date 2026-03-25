import json
import time
from datetime import datetime
from pathlib import Path

import requests

API_KEY = "1da1a8a94afe4d9a983644699fa63e98"
TIMEOUT = 10
REFRESH = 30

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "dashboard" / "wmata_data.json"

BUS_STOPS = [
    {"id": "1000908", "name": "C St NE + 17th St NE"},
    {"id": "1000967", "name": "D St NE + 17th St NE"},
    {"id": "1001095", "name": "Benning Rd NE + 18th St NE"},
    {"id": "1002979", "name": "15th St NE & Isherwood St NE"},
    {"id": "1000950", "name": "8th St NE + D St NE"},
]

METRO_STATIONS = [
    {"code": "D05", "name": "Stadium-Armory"},
    {"code": "B03", "name": "Union Station"},
]


def get_json(url: str, params: dict) -> dict:
    response = requests.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def keep_train_prediction(item: dict) -> bool:
    raw = str(item.get("Min", "")).strip()

    if raw in {"ARR", "BRD"}:
        return False

    try:
        return int(raw) >= 3
    except Exception:
        return False


def fetch_bus(stop: dict) -> dict:
    url = "https://api.wmata.com/NextBusService.svc/json/jPredictions"
    params = {
        "StopID": stop["id"],
        "api_key": API_KEY,
    }

    try:
        data = get_json(url, params)
        return {
            "name": data.get("StopName", stop["name"]),
            "items": data.get("Predictions", [])[:4],
            "error": None,
        }
    except Exception as e:
        return {
            "name": stop["name"],
            "items": [],
            "error": str(e),
        }


def fetch_metro(station: dict) -> dict:
    url = f"https://api.wmata.com/StationPrediction.svc/json/GetPrediction/{station['code']}"
    params = {"api_key": API_KEY}

    try:
        data = get_json(url, params)
        filtered_trains = [
            item for item in data.get("Trains", [])
            if keep_train_prediction(item)
        ]

        return {
            "name": station["name"],
            "items": filtered_trains[:4],
            "error": None,
        }
    except Exception as e:
        return {
            "name": station["name"],
            "items": [],
            "error": str(e),
        }


def build_output() -> dict:
    return {
        "updated": datetime.now().strftime("%I:%M:%S %p"),
        "bus": [fetch_bus(stop) for stop in BUS_STOPS],
        "metro": [fetch_metro(station) for station in METRO_STATIONS],
    }


def write_output(data: dict) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def main_loop():
    print("Starting WMATA updater...")
    print(f"Writing to: {OUTPUT_FILE}")

    while True:
        try:
            output = build_output()
            write_output(output)
            print(f"Updated at {output['updated']}")
        except Exception as e:
            print("ERROR:", e)

        time.sleep(REFRESH)


if __name__ == "__main__":
    main_loop()