import os
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://transitai-frontend.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "TransitAI backend is running"}

@app.get("/routes")
def get_routes():
    return {
        "routes": [
            {"id": 1, "name": "Metro Line 2 + Bus 335", "duration": 28, "crowd": "low"},
            {"id": 2, "name": "BMTC Bus 500C", "duration": 40, "crowd": "moderate"},
            {"id": 3, "name": "Metro Line 1 direct", "duration": 22, "crowd": "high"},
        ]
    }

class RouteRequest(BaseModel):
    from_lat: float
    from_lng: float
    to_name: str

@app.post("/live-routes")
def live_routes(req: RouteRequest):
    import requests as req_lib

    destinations = {
        "mg road": (12.9757, 77.6011),
        "whitefield": (12.9698, 77.7499),
        "home": (12.9352, 77.6245),
        "koramangala": (12.9352, 77.6245),
        "indiranagar": (12.9784, 77.6408),
        "majestic": (12.9767, 77.5713),
        "electronic city": (12.8399, 77.6770),
        "hebbal": (13.0350, 77.5970),
    }

    dest_key = req.to_name.lower().strip()
    dest_coords = destinations.get(dest_key)

    if not dest_coords:
        dest_coords = (12.9757, 77.6011)

    api_key = os.getenv("ORS_API_KEY")
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": api_key}
    body = {
        "coordinates": [
            [req.from_lng, req.from_lat],
            [dest_coords[1], dest_coords[0]]
        ]
    }

    try:
        response = req_lib.post(url, json=body, headers=headers)
        data = response.json()
        segment = data["routes"][0]["segments"][0]
        distance_km = round(data["routes"][0]["summary"]["distance"] / 1000, 1)
        duration_min = round(data["routes"][0]["summary"]["duration"] / 60)

        return {
            "routes": [
                {
                    "id": 1,
                    "name": f"Metro + Bus (recommended)",
                    "duration": round(duration_min * 1.1),
                    "distance": distance_km,
                    "crowd": "low",
                },
                {
                    "id": 2,
                    "name": f"BMTC Direct Bus",
                    "duration": round(duration_min * 1.4),
                    "distance": distance_km,
                    "crowd": "moderate",
                },
                {
                    "id": 3,
                    "name": f"Metro Line 1 Express",
                    "duration": duration_min,
                    "distance": distance_km,
                    "crowd": "high",
                },
            ]
        }
    except Exception as e:
        return {
            "routes": [
                {"id": 1, "name": "Metro + Bus 335", "duration": 28, "distance": 8.2, "crowd": "low"},
                {"id": 2, "name": "BMTC Bus 500C", "duration": 40, "distance": 8.2, "crowd": "moderate"},
                {"id": 3, "name": "Metro Line 1 direct", "duration": 22, "distance": 8.2, "crowd": "high"},
            ]
        }
class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat(req: ChatRequest):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """You are TransitAI, a smart public transport assistant for Bengaluru, India.
                You help commuters with routes, crowd levels, delays, and accessibility.
                Keep answers short, helpful and specific. Use the following live data:
                - Metro Line 2 + Bus 335: 28 min, low crowd, step-free, on time
                - BMTC Bus 500C: 40 min, moderate crowd, delayed 12 min
                - Metro Line 1 direct: 22 min, high crowd, fastest option"""
            },
            {
                "role": "user",
                "content": req.message
            }
        ]
    )
    return {"reply": response.choices[0].message.content}