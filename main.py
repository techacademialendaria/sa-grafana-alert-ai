import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

@app.route("/grafana-alert", methods=["POST"])
def handle_alert():
    data = request.json

    rule_name = data.get("ruleName", "Alerta Grafana")
    labels = data.get("labels", {})
    instance = labels.get("instance", "desconhecida")
    value = data.get("valueString", "?")
    summary = data.get("annotations", {}).get("summary", "Sem resumo")

    prompt = f"""
[ALERTA DO GRAFANA]
Regra: {rule_name}
Instância: {instance}
Valor da métrica: {value}
Resumo: {summary}

1. Diagnostique o problema.
2. Sugira causas prováveis.
3. Dê recomendações técnicas específicas.
"""

    # IA via OpenRouter
    chat = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-4-turbo",
            "messages": [
                {"role": "system", "content": "Você é um engenheiro SRE especialista em PostgreSQL e observabilidade."},
                {"role": "user", "content": prompt}
            ]
        }
    )

    resposta = chat.json()["choices"][0]["message"]["content"]

    # Envia para Discord
    requests.post(DISCORD_WEBHOOK, json={
        "content": f"🚨 **{rule_name}** detectado!",
        "embeds": [{
            "title": f"📊 Diagnóstico automático – {instance}",
            "description": resposta,
            "color": 15158332
        }],
        "allowed_mentions": { "parse": ["everyone"] }
    })

    return {"status": "ok"}, 200

# 🚀 Parte mais importante pro Railway funcionar:
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
