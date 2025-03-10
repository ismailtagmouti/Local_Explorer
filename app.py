from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import googlemaps
from google import genai

app = Flask(__name__, template_folder="templates")
CORS(app)

# Set your API keys here (replace with your actual keys)
WEATHER_API_KEY = "77683cac8a126c60d51a6d3d7756bc06"
GOOGLE_MAPS_API_KEY = "AIzaSyAbFTpavYd31XB9MIH1qCt8f2KzRRvVX3k"
GENAI_API_KEY = "AIzaSyCyrKQufcP8UyweIYWS3g6SVca_IZXTLQw"

gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

def get_weather(lat, lon):
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(weather_url)

    if response.status_code != 200:
        return None

    data = response.json()
    return {
        "location": data.get("name", "Unknown Location"),
        "temperature": round(data["main"]["temp"]),  # Round to match UI format
        "real_feel": round(data["main"]["feels_like"]),  # Feels-like temperature
        "weather": data["weather"][0]["main"],  # Weather condition (Rain, Clear, etc.)
        "description": data["weather"][0]["description"].capitalize(),  # Weather description
        "humidity": data["main"]["humidity"],  # Humidity percentage
        "wind_speed": data["wind"]["speed"],  # Wind speed in km/h
        "wind_gusts": data["wind"].get("gust", 0),  # Wind gusts (if available)
        "cloud_cover": data["clouds"]["all"],  # Cloud coverage percentage
        "icon": f"http://openweathermap.org/img/wn/{data['weather'][0]['icon']}@2x.png",  # Weather icon
        "lat": data["coord"]["lat"],  
        "lon": data["coord"]["lon"]
    }

def find_nearby_places(lat, lon, query="activity", radius=5000):
    places = gmaps.places_nearby(
        location=(lat, lon),
        radius=radius,  # 5km radius
        keyword=query
    )

    indoor_keywords = ["museum", "gallery", "theater", "cinema", "art", "indoor"]
    outdoor_keywords = ["park", "garden", "outdoor", "nature", "trail", "beach"]

    places_list = {"indoor": [], "outdoor": []}

    for place in places.get("results", []):
        name = place.get("name")
        address = place.get("vicinity")
        opening_hours = place.get("opening_hours", {}).get("weekday_text", [])
        website = place.get("website", "Not available")
        rating = place.get("rating", "No ratings")
        phone_number = place.get("formatted_phone_number", "Not available")

        if any(keyword.lower() in name.lower() or keyword.lower() in (place.get("types", [])) for keyword in indoor_keywords):
            category = "indoor"
        elif any(keyword.lower() in name.lower() or keyword.lower() in (place.get("types", [])) for keyword in outdoor_keywords):
            category = "outdoor"
        else:
            category = "indoor"  

        place_details = {
            "name": name,
            "address": address,
            "opening_hours": opening_hours if opening_hours else "Not available",
            "category": category,
            "website": website,
            "rating": rating,
            "phone_number": phone_number
        }

        places_list[category].append(place_details)

    return places_list

# ✅ AI Activity Suggestion (Indoor and Outdoor)
@app.route("/suggest_activity", methods=["POST"])
def suggest_activity():
    data = request.json
    location = data.get("location")
    weather = data.get("weather")
    temperature = data.get("temperature")
    activity_type = data.get("activity_type", "both")  # New parameter to specify 'indoor', 'outdoor', or 'both'

    if not location or not weather or not temperature:
        return jsonify({"error": "Missing required data"}), 400

    # Adjust the prompt based on activity type
    if activity_type == "indoor":
        prompt = f"Suggest an indoor activity for someone in {location} where the weather is {weather} and the temperature is {temperature}°C."
    elif activity_type == "outdoor":
        prompt = f"Suggest an outdoor activity for someone in {location} where the weather is {weather} and the temperature is {temperature}°C."
    else:  # Default to both indoor and outdoor activities
        prompt = f"Suggest an indoor or outdoor activity for someone in {location} where the weather is {weather} and the temperature is {temperature}°C."

    try:
        genai_client = genai.Client(api_key=GENAI_API_KEY)  # Initialize GenAI client
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash",  # Ensure you're using the correct model
            contents=prompt
        )

        suggestion = response.text.strip()
        return jsonify({"suggested_activity": suggestion})

    except Exception as e:
        print(f"Error occurred: {str(e)}")  # Log the error
        return jsonify({"error": "Failed to generate activity suggestion", "message": str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/fetch_weather", methods=["POST"])
def fetch_weather():
    data = request.json
    lat = data.get("lat")
    lon = data.get("lon")

    if not lat or not lon:
        return jsonify({"error": "Missing latitude or longitude"}), 400

    weather_data = get_weather(lat, lon)
    
    if not weather_data:
        return jsonify({"error": "Failed to fetch weather data"}), 500

    return jsonify({"weather": weather_data})

@app.route("/fetch_places", methods=["POST"])
def fetch_places():
    data = request.json
    lat = data.get("lat")
    lon = data.get("lon")

    if not lat or not lon:
        return jsonify({"error": "Missing latitude or longitude"}), 400

    places_list = find_nearby_places(lat, lon, query="activity")
    return jsonify(places_list)

if __name__ == "__main__":
    app.run(debug=True)
