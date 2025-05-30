import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# 🔐 Load secrets
load_dotenv()
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

app = Flask(__name__)

@app.route("/grafana-alert", methods=["POST"])
def handle_alert():
    data = request.json
    print("📦 Payload recebido:", data)

    # 1️⃣ Fallback seguro
    try:
        rule_name = data.get("ruleName") or data.get("alertName") or "Alerta Grafana"
        labels = data.get("labels", {}) or data.get("CommonLabels", {})
        annotations = data.get("annotations", {}) or data.get("CommonAnnotations", {})
        value = data.get("valueString", "?")
        summary = annotations.get("summary", "Sem descrição.")

        instance = labels.get("instance", "instância-desconhecida")
        database = labels.get("database", "banco-desconhecido")
        user = labels.get("user", "desconhecido")

        prompt = f"""
[🚨 ALERTA DO GRAFANA]
Regra: {rule_name}
Instância: {instance}
Banco: {database}
Usuário: {user}
Valor da métrica: {value}
Resumo: {summary}

1. Diagnostique o problema.
2. Sugira causas prováveis.
3. Dê recomendações técnicas específicas.
4. Escreva instruções em Português Brasil.
"""

    except Exception as e:
        print("❌ Erro ao montar prompt:", e)
        prompt = "Recebido um alerta do Grafana, mas não foi possível extrair os dados corretamente."

    # 2️⃣ Consulta IA
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mistral-7b-instruct",
                "messages": [
                    { "role": "system", "content": "Você é um engenheiro SRE especialista em PostgreSQL e observabilidade." },
                    { "role": "user", "content": prompt }
                ]
            }
        )
        response.raise_for_status()
        ia_reply = response.json()["choices"][0]["message"]["content"]

    except Exception as e:
        print("❌ Erro ao consultar IA:", e)
        ia_reply = "⚠️ Erro ao consultar a IA. Verifique os logs para detalhes."

    # 3️⃣ Envia para Discord
    try:
        embed = {
            "title": f"📊 Diagnóstico automático – {instance}",
            "description": ia_reply,
            "color": 15158332
        }

        discord_payload = {
            "content": f"@everyone 🚨 **{rule_name}** detectado!",
            "embeds": [embed],
            "allowed_mentions": { "parse": ["everyone"] }
        }

        resp = requests.post(DISCORD_WEBHOOK, json=discord_payload)
        resp.raise_for_status()
        print("✅ Alerta enviado ao Discord:", resp.status_code)

    except Exception as e:
        print("❌ Falha ao enviar para o Discord:", e)

    return jsonify({"status": "ok"}), 200

# 4️⃣ Run
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
