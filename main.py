import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

# 🔐 Carrega variáveis de ambiente
load_dotenv()
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

app = Flask(__name__)

@app.route("/grafana-alert", methods=["POST"])
def handle_alert():
    data = request.json
    print("🚨 Alerta recebido:", data)

    # ✅ Fallback: tenta extrair a mensagem customizada ou monta com base nas labels
    if "message" in data and data["message"].strip():
        mensagem = data["message"]
    else:
        rule_name = data.get("ruleName", "Alerta Grafana")
        labels = data.get("labels", {})
        instance = labels.get("instance", "desconhecida")
        value = data.get("valueString", "?")
        summary = data.get("annotations", {}).get("summary", "Sem resumo")

        mensagem = f"""Regra: {rule_name}
Instância: {instance}
Valor da métrica: {value}
Resumo: {summary}"""

    # 🔍 Prompt enviado à IA
    prompt = f"""
[ALERTA DO GRAFANA]
{mensagem}

1. Diagnostique o problema.
2. Sugira causas prováveis.
3. Dê recomendações técnicas específicas.
4. Informe as instruções em Português Brasil.
"""

    try:
        # 💬 Chamada à OpenRouter
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mistral-7b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": "Você é um engenheiro SRE especialista em PostgreSQL e observabilidade."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        )

        response.raise_for_status()
        ia_json = response.json()
        resposta = ia_json["choices"][0]["message"]["content"]

    except Exception as e:
        print("❌ Erro ao consultar IA:", e)
        print("📦 Resposta crua:", getattr(response, "text", "sem resposta"))
        resposta = "⚠️ Erro ao consultar a IA. Verifique logs para detalhes."

    # 📤 Envia alerta para Discord
    try:
        title = "Diagnóstico automático"
        instance = data.get("labels", {}).get("instance", "desconhecida")

        discord_payload = {
            "content": f"@everyone 🚨 **Alerta Grafana** detectado!",
            "embeds": [
                {
                    "title": f"📊 {title} – {instance}",
                    "description": resposta,
                    "color": 15158332  # vermelho
                }
            ],
            "allowed_mentions": {"parse": ["everyone"]}
        }

        discord_response = requests.post(DISCORD_WEBHOOK, json=discord_payload)
        discord_response.raise_for_status()
        print("✅ Alerta enviado ao Discord:", discord_response.status_code)

    except Exception as e:
        print("❌ Falha ao enviar alerta ao Discord:", e)

    return {"status": "ok"}, 200


# 🚀 Railway & Localhost
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
