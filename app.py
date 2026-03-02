from flask import Flask, jsonify, request
import requests
import os

app = Flask(__name__)

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
WORKSPACE_ID = os.getenv("WORKSPACE_ID")
DATASET_ID = os.getenv("DATASET_ID")
API_KEY = os.getenv("API_KEY")

# Endpoint para verificar que el servidor funciona
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "API funcionando correctamente 🚀"})


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
    return response.json().get("access_token")


def refresh_dataset():
    token = get_token()

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}/datasets/{DATASET_ID}/refreshes"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Enviamos body vacío {}
    response = requests.post(url, headers=headers, json={})

    return response.status_code, response.text


@app.route("/refresh", methods=["GET"])
def trigger_refresh():
    key = request.args.get("key")

    # Validación de API KEY
    if API_KEY and key != API_KEY:
        return jsonify({"error": "No autorizado"}), 401

    try:
        status, text = refresh_dataset()

        return jsonify({
            "mensaje": "Solicitud enviada a Power BI",
            "status_code": status,
            "detalle": text
        }), status

    except requests.exceptions.HTTPError as http_err:
        return jsonify({
            "error": "Error HTTP al llamar Power BI",
            "detalle": str(http_err)
        }), 500

    except Exception as e:
        return jsonify({
            "error": "Error inesperado",
            "detalle": str(e)
        }), 500


if __name__ == "__main__":
    # IMPORTANTE: Render usa puerto dinámico
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
