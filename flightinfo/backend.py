import json, math, os, requests
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()
LAT_DEFAULT = 49.0
LON_DEFAULT = 6.0
RADIUS_KM = 30
PHOTO_CACHE = {}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_plane_photo(hex_code):
    if hex_code in PHOTO_CACHE: return PHOTO_CACHE[hex_code]
    try:
        r = requests.get(f"https://api.planespotters.net/pub/photos/hex/{hex_code}", timeout=2)
        if r.status_code == 200 and r.json().get("photos"):
            PHOTO_CACHE[hex_code] = r.json()["photos"][0]["thumbnail_large"]["src"]
            return PHOTO_CACHE[hex_code]
    except: pass
    PHOTO_CACHE[hex_code] = None
    return None

@app.get("/api/planes")
def get_planes(radius: float = RADIUS_KM):
    results = []
    try:
        with open("/run/dump1090-fa/aircraft.json", "r") as f:
            for ac in json.load(f).get("aircraft", []):
                if "lat" in ac and "lon" in ac:
                    dist = haversine(LAT_DEFAULT, LON_DEFAULT, ac["lat"], ac["lon"])
                    if dist <= radius:
                        results.append({
                            "hex": ac.get("hex"),
                            "flight": ac.get("flight", "").strip(),
                            "alt_baro": ac.get("alt_baro"),
                            "speed_kmh": int(ac.get("gs", 0) * 1.852) if ac.get("gs") else None,
                            "track": ac.get("track"),
                            "v_speed": ac.get("baro_rate"),
                            "distance_km": round(dist, 1),
                            "photo": get_plane_photo(ac.get("hex"))
                        })
    except: return {"error": "aircraft.json not found"}
    return {"planes": results}

app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/")
def read_index(): return FileResponse("static/index.html")
