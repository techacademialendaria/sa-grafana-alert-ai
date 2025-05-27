import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# 🔐 Carrega as variáveis do ambiente
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

@app.route("/grafana-alert", methods=["POST"])
def handle_alert():
    data = request.json

    rule_name = data.get("ruleName", "Alerta Grafana")
    labels = data.get("labels", {})
    instance = labels.get("instance") or "desconhecida"
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
4. Informe as instruções em Português Brasil.
"""

    print("🚨 Alerta recebido:", rule_name)

    try:
        # 🔍 Consulta IA via OpenRouter
        chat = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mistral-7b-instruct",
                "messages": [
                    {"role": "system", "content": "Você é um engenheiro SRE especialista em PostgreSQL e observabilidade."},
                    {"role": "user", "content": prompt}
                ]
            }
        )

        ia_response = chat.json()
        resposta = ia_response["choices"][0]["message"]["content"]

    except Exception as e:
        print("❌ Erro ao processar resposta da IA:", e)
        print("📦 Resposta da IA:", chat.text)
        resposta = "⚠️ Erro ao consultar a IA. Verifique logs para detalhes."

    # 📤 Envia mensagem para Discord
    try:
        discord_response = requests.post(DISCORD_WEBHOOK, json={
            "content": f"@everyone 🚨 **{rule_name}** detectado!",
            "embeds": [{
                "title": f"📊 Diagnóstico automático – {instance}",
                "description": resposta,
                "color": 15158332
            }],
            "allowed_mentions": { "parse": ["everyone"] }
        })

        print("✅ Alerta enviado ao Discord:", discord_response.status_code)

    except Exception as e:
        print("❌ Erro ao enviar alerta ao Discord:", e)

    return {"status": "ok"}, 200

# 🌐 Executa localmente ou na Railway
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
