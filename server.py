from flask import Flask
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running ✅"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render automatically port assign karega
    app.run(host="0.0.0.0", port=port)
