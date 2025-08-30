from flask import Flask
import multiprocessing
import os
import signal
import Extractor

app = Flask(__name__)
bot_process = None

# --- Run bot ---
def run_bot():
    Extractor.main()

# --- Flask route for UptimeRobot ---
@app.route("/")
def home():
    global bot_process
    if bot_process is not None and bot_process.is_alive():
        return "✅ Bot running"
    else:
        return "❌ Bot stopped"

if __name__ == "__main__":
    # Start bot process
    bot_process = multiprocessing.Process(target=run_bot)
    bot_process.start()

    # Start flask server (UptimeRobot will ping this)
    port = int(os.environ.get("PORT", 10000))
    try:
        app.run(host="0.0.0.0", port=port)
    finally:
        if bot_process is not None:
            os.kill(bot_process.pid, signal.SIGTERM)
