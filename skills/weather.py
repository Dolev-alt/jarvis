import os
import requests


def execute(params):
    city = params.get("city") or os.getenv("JARVIS_CITY", "Tel Aviv")
    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()

    if not api_key:
        return "Sir, I don't have a weather API key configured. Add OPENWEATHER_API_KEY to .env — it's free at openweathermap.org."

    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            return f"Sir, the weather service returned an error ({resp.status_code})."

        data = resp.json()
        desc = data["weather"][0]["description"]
        temp = round(data["main"]["temp"])
        feels = round(data["main"]["feels_like"])
        humidity = data["main"]["humidity"]
        wind = round(data["wind"]["speed"] * 3.6)  # m/s -> km/h

        return (
            f"Current conditions in {city}: {temp}°C (feels like {feels}°C), "
            f"{desc}, humidity {humidity}%, wind {wind} km/h."
        )
    except Exception as e:
        return f"Sir, I was unable to retrieve the weather data: {e}"
