import os
import time
import random
import requests
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Point to the ingestion service
API_URL = os.getenv("API_URL", "http://axion-ingestion-service.default.svc.cluster.local:80/api/v1/telemetry/ingest")
INTERVAL_SECONDS = int(os.getenv("INTERVAL_SECONDS", "5"))

# ---------------------------------------------------------------------------
# Device Catalog
# ---------------------------------------------------------------------------
DEVICES = [
    {"id": "PUMP_N01", "type": "PUMP", "region": "NORTH_PLANT", "temp_base": 60, "vib_base": 2.5, "cur_base": 12.0},
    {"id": "PUMP_N02", "type": "PUMP", "region": "NORTH_PLANT", "temp_base": 65, "vib_base": 3.0, "cur_base": 14.5},
    {"id": "PUMP_N03", "type": "PUMP", "region": "NORTH_PLANT", "temp_base": 62, "vib_base": 2.8, "cur_base": 13.0},
    {"id": "MOTOR_N01", "type": "MOTOR", "region": "NORTH_PLANT", "temp_base": 75, "vib_base": 4.2, "cur_base": 30.0},
    {"id": "COMPRESSOR_N01", "type": "COMPRESSOR", "region": "NORTH_PLANT", "temp_base": 80, "vib_base": 5.5, "cur_base": 40.0},
    
    {"id": "PUMP_S01", "type": "PUMP", "region": "SOUTH_PLANT", "temp_base": 55, "vib_base": 2.0, "cur_base": 11.5},
    {"id": "MOTOR_S01", "type": "MOTOR", "region": "SOUTH_PLANT", "temp_base": 78, "vib_base": 4.5, "cur_base": 35.0},
    {"id": "MOTOR_S02", "type": "MOTOR", "region": "SOUTH_PLANT", "temp_base": 80, "vib_base": 4.8, "cur_base": 32.0},
    {"id": "COMPRESSOR_S01", "type": "COMPRESSOR", "region": "SOUTH_PLANT", "temp_base": 82, "vib_base": 5.0, "cur_base": 42.0},
    
    {"id": "COMPRESSOR_E01", "type": "COMPRESSOR", "region": "EAST_REFINERY", "temp_base": 82, "vib_base": 5.5, "cur_base": 45.0},
    {"id": "PUMP_E01", "type": "PUMP", "region": "EAST_REFINERY", "temp_base": 70, "vib_base": 3.5, "cur_base": 15.0},
    {"id": "MOTOR_E01", "type": "MOTOR", "region": "EAST_REFINERY", "temp_base": 76, "vib_base": 4.5, "cur_base": 31.0},

    {"id": "PUMP_W01", "type": "PUMP", "region": "WEST_REFINERY", "temp_base": 58, "vib_base": 2.2, "cur_base": 12.5},
    {"id": "MOTOR_W01", "type": "MOTOR", "region": "WEST_REFINERY", "temp_base": 74, "vib_base": 4.0, "cur_base": 29.0},
]

# Track current state for random walk
state = {}
for d in DEVICES:
    state[d["id"]] = {
        "temperature": d["temp_base"],
        "vibration": d["vib_base"],
        "current": d["cur_base"]
    }

def generate_payload(device):
    """Generate the next random-walk data point for a device."""
    did = device["id"]
    
    # Random walk: drift slightly from current state, but revert towards base to prevent permanent spikes
    s = state[did]
    
    # Revert to mean (base value)
    s["temperature"] += (device["temp_base"] - s["temperature"]) * 0.1
    s["vibration"] += (device["vib_base"] - s["vibration"]) * 0.1
    s["current"] += (device["cur_base"] - s["current"]) * 0.1

    # Add random noise
    s["temperature"] += random.uniform(-1.5, 1.5)
    s["vibration"] += random.uniform(-0.2, 0.2)
    s["current"] += random.uniform(-0.5, 0.5)
    
    # Keep bounds somewhat realistic around the base
    s["temperature"] = max(20.0, min(150.0, s["temperature"]))
    s["vibration"] = max(0.0, min(15.0, s["vibration"]))
    s["current"] = max(0.0, min(100.0, s["current"]))

    # Simulate an occasional anomaly (1% chance)
    if random.random() < 0.01:
        s["temperature"] += 20.0
        s["vibration"] += 5.0
        print(f"ANOMALY TRIGGERED on {did}")

    return {
        "deviceId": did,
        "deviceType": device["type"],
        "refineryRegion": device["region"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "temperature": round(s["temperature"], 2),
            "vibration": round(s["vibration"], 2),
            "current": round(s["current"], 2)
        }
    }

def main():
    print(f"Starting Data Simulator. Interval: {INTERVAL_SECONDS}s. API: {API_URL}")
    while True:
        for device in DEVICES:
            payload = generate_payload(device)
            try:
                resp = requests.post(API_URL, json=payload, timeout=2)
                if resp.status_code == 201:
                    print(f"Sent {payload['deviceId']} -> OK")
                else:
                    print(f"Sent {payload['deviceId']} -> FAILED ({resp.status_code}): {resp.text}")
            except Exception as e:
                print(f"Sent {payload['deviceId']} -> NETWORK ERROR: {e}")
        
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
