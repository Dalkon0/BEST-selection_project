import os
import json
import datetime


_STORAGE = os.getenv("LOG_STORAGE", "local").lower()
_LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
_MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
_MONGO_DB = os.getenv("MONGO_DB", "uav_telemetry")


def log_pipeline(
    model: str,
    prompt: str,
    response: str,
    metrics: dict,
    prompt_tokens: int,
    completion_tokens: int,
    duration_s: float,
    filename: str = "",
):
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "filename": filename,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "duration_s": round(duration_s, 3),
        "metrics_snapshot": metrics,
        "prompt": prompt,
        "response": response,
    }

    if _STORAGE == "mongodb":
        _log_to_mongo(entry)
    else:
        _log_to_file(entry)


def _log_to_file(entry: dict):
    os.makedirs(_LOG_DIR, exist_ok=True)
    date_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    path = os.path.join(_LOG_DIR, f"ai_pipeline_{date_str}.json")

    records = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                records = json.load(f)
        except (json.JSONDecodeError, IOError):
            records = []

    records.append(entry)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def _log_to_mongo(entry: dict):
    try:
        from pymongo import MongoClient
        client = MongoClient(_MONGO_URI, serverSelectionTimeoutMS=3000)
        db = client[_MONGO_DB]
        db["ai_pipeline"].insert_one(entry)
        client.close()
    except Exception as e:
        _log_to_file(entry)

def get_recent_logs(limit=10):
    if _STORAGE == "mongodb":
        try:
            from pymongo import MongoClient, DESCENDING
            client = MongoClient(_MONGO_URI, serverSelectionTimeoutMS=2000)
            db = client[_MONGO_DB]
            logs = list(db["ai_pipeline"].find().sort("timestamp", DESCENDING).limit(limit))
            client.close()
            for log in logs: log.pop("_id", None)
            return logs
        except Exception:
            return []
    else:
        os.makedirs(_LOG_DIR, exist_ok=True)
        all_logs = []
        try:
            files = sorted([f for f in os.listdir(_LOG_DIR) if f.startswith("ai_pipeline_")], reverse=True)
            for f in files:
                with open(os.path.join(_LOG_DIR, f), "r", encoding="utf-8") as file:
                    all_logs.extend(json.load(file))
                if len(all_logs) >= limit: break
            return sorted(all_logs, key=lambda x: x["timestamp"], reverse=True)[:limit]
        except Exception:
            return []
