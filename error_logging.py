import json, datetime, os

def log_error(context: str, exit_code: int, error_msg: str):
    """Append a JSON line to pipeline_errors.log.
    context: description of where the error occurred.
    exit_code: the non‑zero exit code or -1 for exceptions.
    error_msg: string representation of the error.
    """
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "context": context,
        "exit_code": exit_code,
        "error": str(error_msg)
    }
    log_path = os.path.join(os.path.dirname(__file__), "pipeline_errors.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
