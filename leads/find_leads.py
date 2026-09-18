"""
Busca negócios brasileiros sem site cadastrado no Google Places, para usar
como leads de prospecção. Usa a Places API (Text Search + Place Details).

Uso:
    python leads/find_leads.py --cidade "Aracaju, SE" --tipo "hamburgueria" --max 20
"""

import argparse
import os
import re
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GOOGLE_PLACES_API_KEY, LEADS_CSV
from leads.lead_store import load_leads, save_leads, upsert_lead

TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def _require_api_key():
    if not GOOGLE_PLACES_API_KEY:
        raise SystemExit(
            "GOOGLE_PLACES_API_KEY não configurada. Copie .env.example para .env "
            "e preencha a chave (Google Cloud Console > Places API)."
        )


def text_search(query, max_results=20):
    _require_api_key()
    results = []
    params = {"query": query, "key": GOOGLE_PLACES_API_KEY, "language": "pt-BR"}
    while True:
        resp = requests.get(TEXT_SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            raise RuntimeError(f"Places Text Search falhou: {data.get('status')} - {data.get('error_message')}")
        results.extend(data.get("results", []))
        next_token = data.get("next_page_token")
        if not next_token or len(results) >= max_results:
            break
        # O token só fica válido alguns segundos depois de emitido.
        time.sleep(2)
        params = {"pagetoken": next_token, "key": GOOGLE_PLACES_API_KEY}
    return results[:max_results]


def get_place_details(place_id):
    _require_api_key()
    fields = ",".join(
        [
            "name",
            "formatted_address",
            "formatted_phone_number",
            "international_phone_number",
            "website",
            "rating",
            "user_ratings_total",
            "url",
            "opening_hours",
            "business_status",
        ]
    )
    params = {"place_id": place_id, "fields": fields, "key": GOOGLE_PLACES_API_KEY, "language": "pt-BR"}
    resp = requests.get(DETAILS_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "OK":
        return None
    return data.get("result", {})


def phone_to_e164_br(phone):
    """Converte um telefone BR (com DDD) para o formato usado em wa.me (55DDDNUMERO)."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("55") and len(digits) >= 12:
        return digits
    if len(digits) in (10, 11):  # DDD + número, sem código do país
        return "55" + digits
    return digits


def is_probable_whatsapp(e164_digits):
    """Heurística: número de celular BR (9 dígitos após o DDD) provavelmente tem WhatsApp."""
    if not e164_digits.startswith("55"):
        return False
    resto = e164_digits[2:]
    return len(resto) == 11 and resto[2] == "9"


def find_leads(cidade, tipo_negocio, max_results=20):
    query = f"{tipo_negocio} em {cidade}"
    print(f"Buscando: '{query}'...")
    candidatos = text_search(query, max_results=max_results)
    print(f"{len(candidatos)} resultado(s) encontrado(s). Verificando detalhes...")

    leads_by_id = load_leads(LEADS_CSV)
    novos = 0

    for c in candidatos:
        place_id = c.get("place_id")
        if not place_id:
            continue
        details = get_place_details(place_id)
        if not details or details.get("business_status") not in (None, "OPERATIONAL"):
            continue
        if details.get("website"):
            continue  # já tem site, não é lead

        phone = details.get("international_phone_number") or details.get("formatted_phone_number", "")
        e164 = phone_to_e164_br(phone)
        if not is_probable_whatsapp(e164):
            continue  # sem número de celular identificável, pula

        lead = {
            "place_id": place_id,
            "name": details.get("name", c.get("name", "")),
            "address": details.get("formatted_address", c.get("formatted_address", "")),
            "city": cidade,
            "phone_e164": e164,
            "phone_display": phone,
            "rating": details.get("rating", ""),
            "user_ratings_total": details.get("user_ratings_total", ""),
            "maps_url": details.get("url", ""),
        }
        upsert_lead(leads_by_id, lead)
        novos += 1
        # Respeita rate limit da API
        time.sleep(0.2)

    save_leads(LEADS_CSV, leads_by_id)
    print(f"{novos} lead(s) sem site adicionados/atualizados em {LEADS_CSV}")
    return novos


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cidade", required=True, help='Ex: "Aracaju, SE"')
    parser.add_argument("--tipo", required=True, help='Ex: "hamburgueria", "salão de beleza"')
    parser.add_argument("--max", type=int, default=20, dest="max_results")
    args = parser.parse_args()
    find_leads(args.cidade, args.tipo, args.max_results)
