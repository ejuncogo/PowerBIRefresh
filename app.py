from flask import Flask, jsonify, request
import requests
import os
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

# =========================
# Variables de entorno
# =========================
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
WORKSPACE_ID = os.getenv("WORKSPACE_ID")
DATASET_ID = os.getenv("DATASET_ID")
API_KEY = os.getenv("API_KEY")

# =========================
# 🔐 Obtener token
# =========================
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

# =========================
# 🔍 Verificar si hay refresh corriendo
# =========================
def is_refresh_running():
    token = get_token()

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}/datasets/{DATASET_ID}/refreshes?$top=1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    if "value" in data and len(data["value"]) > 0:
        status = data["value"][0].get("status", "")
        return status in ["InProgress", "Unknown"]

    return False

# =========================
# 🚀 Disparar refresh
# =========================
def refresh_dataset():
    token = get_token()

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}/datasets/{DATASET_ID}/refreshes"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers)

    if response.status_code == 400:
        return {
            "status": "in_progress",
            "message": "Ya hay una actualizacion en curso"
        }

    if response.status_code in [200, 202]:
        return {
            "status": "started",
            "message": "Actualizacion iniciada correctamente"
        }

    return {
        "status": "error",
        "message": f"Error al iniciar actualizacion: {response.text}"
    }

# =========================
# 📊 Último refresh (SOLO FECHA)
# =========================
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
                end_time_utc = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))

                # Ajuste a hora local (Colombia UTC-5)
                end_time_local = end_time_utc - timedelta(hours=5)

                return {
                    "date": end_time_local.strftime("%Y-%m-%d")
                }

    return {
        "date": None
    }

# =========================
# 🌐 Endpoint principal
# =========================
@app.route("/refresh", methods=["GET"])
def trigger_refresh():
    key = request.args.get("key")

    if API_KEY and key != API_KEY:
        return jsonify({
            "status": "error",
            "message": "No autorizado"
        }), 401

    try:
        # 👇 Si ya hay proceso corriendo
        if is_refresh_running():
            last = last_refresh_time()
            return jsonify({
                "status": "in_progress",
                "message": "Ya hay una actualizacion en curso",
                "last_refresh": last
            }), 200

        # 👇 Iniciar actualización
        result = refresh_dataset()
        last = last_refresh_time()

        return jsonify({
            "status": result["status"],
            "message": result["message"],
            "last_refresh": last
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error interno: {str(e)}"
        }), 500

# =========================
# ▶️ Run
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
