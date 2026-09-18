import csv
import os
from datetime import datetime, timezone

FIELDNAMES = [
    "place_id",
    "source",
    "name",
    "address",
    "city",
    "phone_e164",
    "phone_display",
    "rating",
    "user_ratings_total",
    "maps_url",
    "lat",
    "lon",
    "opening_hours_raw",
    "site_slug",
    "site_path",
    "status",
    "last_updated",
]


def load_leads(csv_path):
    if not os.path.exists(csv_path):
        return {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["place_id"]: row for row in reader}


def save_leads(csv_path, leads_by_id):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in leads_by_id.values():
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})


def upsert_lead(leads_by_id, lead):
    existing = leads_by_id.get(lead["place_id"])
    if existing:
        # Preserva o status e os campos já preenchidos pelas etapas seguintes
        # do funil (site gerado, proposta enviada, etc.) em vez de sobrescrever.
        for key in ("site_slug", "site_path", "status"):
            lead.setdefault(key, existing.get(key, ""))
    lead.setdefault("status", "novo")
    lead["last_updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    leads_by_id[lead["place_id"]] = lead
    return leads_by_id
