import json
import urllib.request
import ssl

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

_UNIT_MAP = {
    "km_to_miles": lambda v: v * 0.621371,
    "miles_to_km": lambda v: v * 1.60934,
    "kg_to_lbs": lambda v: v * 2.20462,
    "lbs_to_kg": lambda v: v * 0.453592,
    "cm_to_inches": lambda v: v * 0.393701,
    "inches_to_cm": lambda v: v * 2.54,
    "m_to_feet": lambda v: v * 3.28084,
    "feet_to_m": lambda v: v * 0.3048,
    "c_to_f": lambda v: v * 9/5 + 32,
    "f_to_c": lambda v: (v - 32) * 5/9,
    "liters_to_gallons": lambda v: v * 0.264172,
    "gallons_to_liters": lambda v: v * 3.78541,
}


def _fetch_exchange_rate(from_currency, to_currency):
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency.upper()}"
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/1.0"})
        with urllib.request.urlopen(req, timeout=8, context=_ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        rates = data.get("rates", {})
        rate = rates.get(to_currency.upper())
        if rate:
            return rate
    except Exception as e:
        print(f"[convert] Exchange rate fetch failed: {e}")
    return None


def execute(params):
    chat = params.get("_chat")

    value_str = params.get("value", "")
    from_unit = params.get("from", "").strip().lower()
    to_unit = params.get("to", "").strip().lower()
    expression = params.get("expression", "").strip()

    if expression and chat:
        try:
            prompt = (
                f"Convert: {expression}\n"
                "If this is a unit conversion, calculate it. If it's a currency conversion, "
                "provide the approximate current rate. "
                "Return ONLY the result with units, e.g. '160.93 km' or '~3,750 ILS'. Nothing else."
            )
            response = chat.send_message(prompt)
            if response and hasattr(response, "text"):
                return response.text.strip()
        except Exception:
            pass

    try:
        value = float(value_str)
    except (ValueError, TypeError):
        if expression:
            return f"Could not parse conversion: {expression}"
        return "No value provided. Use expression='100 USD to ILS' or value=100, from='km', to='miles'."

    key = f"{from_unit}_to_{to_unit}"
    if key in _UNIT_MAP:
        result = _UNIT_MAP[key](value)
        return f"{value} {from_unit} = {result:.2f} {to_unit}"

    if len(from_unit) == 3 and len(to_unit) == 3:
        rate = _fetch_exchange_rate(from_unit, to_unit)
        if rate:
            result = value * rate
            return f"{value} {from_unit.upper()} = {result:.2f} {to_unit.upper()} (rate: {rate:.4f})"
        return f"Could not fetch exchange rate for {from_unit.upper()} → {to_unit.upper()}."

    if chat:
        try:
            prompt = f"Convert {value} {from_unit} to {to_unit}. Return ONLY the numeric result with unit."
            response = chat.send_message(prompt)
            if response and hasattr(response, "text"):
                return response.text.strip()
        except Exception:
            pass

    return f"Unknown conversion: {from_unit} to {to_unit}. Supported: {', '.join(k.replace('_to_', '→') for k in _UNIT_MAP.keys())}, and 3-letter currency codes."
