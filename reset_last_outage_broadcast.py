#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient

SKIP_ID = int(os.getenv("SKIP_TELEGRAM_ID", "80958502"))
GAP = timedelta(minutes=int(os.getenv("LAST_RUN_GAP_MINUTES", "120")))
DRY = os.getenv("DRY_RUN", "").strip().lower() in {"1", "true", "yes"}


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def main() -> int:
    uri = os.getenv("MONGO_URI")
    if not uri:
        print("Немає MONGO_URI", file=sys.stderr)
        return 1
    db_name = os.getenv("MONGO_DB") or "vidkluchennya"
    col = MongoClient(uri, serverSelectionTimeoutMS=8000)[db_name]["user_outage_notified"]

    latest = col.find_one(
        {"notified_at": {"$type": "date"}},
        sort=[("notified_at", -1)],
    )
    if not latest or not latest.get("notified_at"):
        print("user_outage_notified порожня — нічого скидати")
        return 0

    latest_raw = latest["notified_at"]
    prev = _aware(latest_raw)
    cluster_raw = latest_raw
    scanned = 0
    for doc in col.find(
        {"notified_at": {"$type": "date"}},
        {"notified_at": 1},
    ).sort("notified_at", -1):
        raw = doc["notified_at"]
        ts = _aware(raw)
        scanned += 1
        if prev - ts > GAP:
            break
        cluster_raw = raw
        prev = ts

    skip_ids = [SKIP_ID, str(SKIP_ID)]
    window = {"notified_at": {"$gte": cluster_raw, "$lte": latest_raw}}
    query = {
        **window,
        "dedup_key": {"$not": {"$regex": r"^gone\|"}},
        "telegram_id": {"$nin": skip_ids},
        "_id": {"$not": {"$regex": rf"^{SKIP_ID}:"}},
    }

    total = col.count_documents(query)
    kept = col.count_documents({**window, "telegram_id": {"$in": skip_ids}})
    users = col.distinct("telegram_id", query)
    shown = ", ".join(str(u) for u in users[:50])
    if len(users) > 50:
        shown += " …"

    print(
        f"остання розсилка: {_aware(cluster_raw).isoformat()} … "
        f"{_aware(latest_raw).isoformat()} (скан={scanned}, gap={GAP})"
    )
    print(
        f"до скидання: рядків={total}, користувачів={len(users)}, "
        f"лишаємо {SKIP_ID}: рядків у вікні={kept}"
    )
    print(f"користувачі: {shown}")

    if DRY:
        print("DRY_RUN — нічого не видалено")
        return 0
    if total == 0:
        print("немає рядків для скидання")
        return 0

    deleted = col.delete_many(query).deleted_count
    print(f"видалено={deleted} — для цих людей статус останньої розсилки тепер false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
