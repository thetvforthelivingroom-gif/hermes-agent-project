#!/usr/bin/env python3
"""Alert script for new entries in pipeline_errors.log.

It tracks the last processed line in .last_error_pos and sends any new JSON log entries
as Telegram messages using bot token and chat ID from environment variables.
Network errors are caught and logged; the script never crashes.
"""
import os
import sys
import json
import urllib.request
import urllib.parse

def load_last_position(state_path):
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return 0

def save_last_position(state_path, pos):
    try:
        with open(state_path, "w", encoding="utf-8") as f:
            f.write(str(pos))
    except Exception as e:
        log(f"Failed to save state: {e}")

def log(message):
    try:
        with open(os.path.join(os.path.dirname(__file__), "alert_script.log"), "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass  # If logging fails, swallow silently

def send_telegram(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()

def main():
    # Environment variables
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log("Telegram token or chat ID not set in environment.")
        sys.exit(1)

    log_path = os.path.join(os.path.dirname(__file__), "pipeline_errors.log")
    state_path = os.path.join(os.path.dirname(__file__), ".last_error_pos")

    if not os.path.isfile(log_path):
        log(f"Log file not found: {log_path}")
        sys.exit(1)

    # Load lines
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        log(f"Failed to read log file: {e}")
        sys.exit(1)

    last_pos = load_last_position(state_path)
    new_entries = lines[last_pos:]
    if not new_entries:
        log("No new error entries.")
        sys.exit(0)

    for idx, line in enumerate(new_entries, start=last_pos + 1):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            text = f"<b>Pipeline Error</b>\nTimestamp: {entry.get('timestamp')}\nContext: {entry.get('context')}\nExit: {entry.get('exit_code')}\nError: {entry.get('error')}"
            send_telegram(token, chat_id, text)
            log(f"Sent alert for line {idx}.")
        except Exception as e:
            log(f"Failed to process line {idx}: {e}")
    # Update position
    save_last_position(state_path, len(lines))
    log("Alert script completed.")

if __name__ == "__main__":
    main()
