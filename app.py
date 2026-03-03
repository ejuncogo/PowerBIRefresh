from flask import Flask, jsonify, request
import requests
import os
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

# Variables de entorno
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
WORKSPACE_ID = os.getenv("WORKSPACE_ID")
DATASET_ID = os.getenv("DATASET_ID")
API_KEY = os.getenv("API_KEY")


# Obtener token de Power BI
def get_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://analysis.windows.net/powerbi/api/.default"
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]


# Disparar refresh del dataset
def refresh_dataset():
    token = get_token()
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}/datasets/{DATASET_ID}/refreshes"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers)
    return response.status_code, response.text


# Obtener último refresh completado (UTC-5)
def last_refresh_time():
    token = get_token()
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}/datasets/{DATASET_ID}/refreshes?$top=10"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    if "value" in data and len(data["value"]) > 0:
        for r in data["value"]:
            end_time_str = r.get("endTime")
            if end_time_str:
                status = r.get("status", "Unknown")

                # Convertir a datetime UTC
                end_time_utc = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))

                # Ajustar a UTC-5
                end_time_local = end_time_utc - timedelta(hours=5)

                # Calcular tiempo transcurrido
                diff = datetime.now(timezone.utc) - end_time_utc
                minutes = int(diff.total_seconds() / 60)

                if minutes < 1:
                    ago = "Hace menos de un minuto"
                elif minutes < 60:
                    ago = f"Hace {minutes} minutos"
                else:
                    hours = minutes // 60
                    ago = f"Hace {hours} horas" if hours < 24 else f"Hace {hours//24} días"

                return end_time_local.strftime("%Y-%m-%d %H:%M:%S"), status, ago

        return None, "Running", "Refresh en curso..."

    return None, None, None


@app.route("/refresh", methods=["GET"])
def trigger_refresh():
    key = request.args.get("key")
    if API_KEY and key != API_KEY:
        return jsonify({"error": "No autorizado"}), 401

    try:
        # Disparar refresh
        trigger_status, trigger_response = refresh_dataset()

        # Obtener último refresh completado
        last_time, last_status, last_ago = last_refresh_time()

        return jsonify({
            "trigger_status": trigger_status,
            "trigger_response": trigger_response,
            "last_refresh_time": last_time,
            "last_refresh_status": last_status,
            "last_refresh_ago": last_ago
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
