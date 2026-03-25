import json
import math
import time
from datetime import datetime
from pathlib import Path

import requests

REFRESH = 30
TIMEOUT = 10

HOME_LAT = 38.895643
HOME_LON = -76.980581
MAX_MILES_LIME = 0.15
MAX_MILES_CABI_FREE = 0.25

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "dashboard" / "bike_data.json"

LIME_URL = "https://data.lime.bike/api/partners/v1/gbfs/washington_dc/free_bike_status.json"
CABI_STATUS_URL = "https://gbfs.capitalbikeshare.com/gbfs/en/station_status.json"
CABI_INFO_URL = "https://gbfs.capitalbikeshare.com/gbfs/en/station_information.json"
CABI_FREE_BIKE_URL = "https://gbfs.lyft.com/gbfs/1.1/dca-cabi/en/free_bike_status.json"

TARGET_CABI_NAMES = [
    "Rosedale Rec Center",
    "15th & F St NE",
    "16th & North Carolina Ave NE",
]


def get_json(url: str) -> dict:
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    def to_rad(deg: float) -> float:
        return deg * math.pi / 180

    earth_radius_miles = 3958.8
    dlat = to_rad(lat2 - lat1)
    dlon = to_rad(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(to_rad(lat1)) * math.cos(to_rad(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_miles * c


def is_near_home(lat: float, lon: float, max_miles: float) -> bool:
    return distance_miles(HOME_LAT, HOME_LON, lat, lon) <= max_miles


def fetch_lime() -> dict:
    try:
        data = get_json(LIME_URL)
        bikes = data.get("data", {}).get("bikes", [])

        nearby_scooters = 0
        nearby_ebikes = 0
        nearby_markers = []

        for bike in bikes:
            lat = bike.get("lat")
            lon = bike.get("lon")
            vehicle_type = str(bike.get("vehicle_type", "")).lower()

            if lat is None or lon is None:
                continue
            if not is_near_home(lat, lon, MAX_MILES_LIME):
                continue

            item_type = "unknown"
            if "scooter" in vehicle_type:
                nearby_scooters += 1
                item_type = "scooter"
            elif "bike" in vehicle_type:
                nearby_ebikes += 1
                item_type = "ebike"

            nearby_markers.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "type": item_type,
                    "distance_miles": round(distance_miles(HOME_LAT, HOME_LON, lat, lon), 3),
                }
            )

        return {
            "ok": True,
            "scooters": nearby_scooters,
            "ebikes": nearby_ebikes,
            "total": nearby_scooters + nearby_ebikes,
            "markers": nearby_markers,
            "error": None,
        }

    except Exception as e:
        return {
            "ok": False,
            "scooters": 0,
            "ebikes": 0,
            "total": 0,
            "markers": [],
            "error": str(e),
        }


def fetch_cabi_docks() -> dict:
    try:
        status_data = get_json(CABI_STATUS_URL)
        info_data = get_json(CABI_INFO_URL)

        statuses = status_data.get("data", {}).get("stations", [])
        infos = info_data.get("data", {}).get("stations", [])
        info_lookup = {station["station_id"]: station for station in infos}

        selected_markers = []
        total_bikes = 0
        total_ebikes = 0
        total_docks = 0

        for station in statuses:
            station_id = station.get("station_id")
            info = info_lookup.get(station_id, {})

            name = info.get("name", f"Station {station_id}")
            if name not in TARGET_CABI_NAMES:
                continue

            lat = info.get("lat")
            lon = info.get("lon")
            if lat is None or lon is None:
                continue

            num_bikes = station.get("num_bikes_available", 0)
            num_ebikes = station.get("num_ebikes_available", 0)
            num_docks = station.get("num_docks_available", 0)

            total_bikes += num_bikes
            total_ebikes += num_ebikes
            total_docks += num_docks

            selected_markers.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "name": name,
                    "bikes": num_bikes,
                    "ebikes": num_ebikes,
                    "docks": num_docks,
                    "distance_miles": round(distance_miles(HOME_LAT, HOME_LON, lat, lon), 3),
                }
            )

        return {
            "ok": True,
            "bikes": total_bikes,
            "ebikes": total_ebikes,
            "docks": total_docks,
            "markers": selected_markers,
            "error": None,
        }

    except Exception as e:
        return {
            "ok": False,
            "bikes": 0,
            "ebikes": 0,
            "docks": 0,
            "markers": [],
            "error": str(e),
        }


def fetch_cabi_free_ebikes() -> dict:
    try:
        data = get_json(CABI_FREE_BIKE_URL)
        bikes = data.get("data", {}).get("bikes", [])

        nearby_total = 0
        nearby_markers = []

        for bike in bikes:
            lat = bike.get("lat")
            lon = bike.get("lon")
            if lat is None or lon is None:
                continue
            if not is_near_home(lat, lon, MAX_MILES_CABI_FREE):
                continue

            nearby_total += 1
            nearby_markers.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "distance_miles": round(distance_miles(HOME_LAT, HOME_LON, lat, lon), 3),
                }
            )

        return {
            "ok": True,
            "total": nearby_total,
            "markers": nearby_markers,
            "error": None,
        }

    except Exception as e:
        return {
            "ok": False,
            "total": 0,
            "markers": [],
            "error": str(e),
        }


def build_output() -> dict:
    return {
        "updated": datetime.now().strftime("%I:%M:%S %p"),
        "home": {
            "lat": HOME_LAT,
            "lon": HOME_LON,
            "max_miles_lime": MAX_MILES_LIME,
            "max_miles_cabi_free": MAX_MILES_CABI_FREE,
        },
        "lime": fetch_lime(),
        "cabi": fetch_cabi_docks(),
        "cabi_free_ebikes": fetch_cabi_free_ebikes(),
    }


def write_output(data: dict) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def main_loop() -> None:
    print("Starting bike updater...")
    print(f"Writing to: {OUTPUT_FILE}")

    while True:
        try:
            output = build_output()
            write_output(output)
            print(
                f"Updated bike data at {output['updated']} | "
                f"Lime total: {output['lime']['total']} | "
                f"CaBi docks: {len(output['cabi']['markers'])} | "
                f"CaBi free ebikes: {output['cabi_free_ebikes']['total']}"
            )
        except Exception as e:
            print("ERROR:", e)

        time.sleep(REFRESH)


if __name__ == "__main__":
    main_loop()