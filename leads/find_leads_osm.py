"""
Alternativa ao Google Places: busca negócios brasileiros sem site usando
OpenStreetMap (Nominatim para geocodificar a cidade + Overpass API para
buscar os locais). Gratuito e sem necessidade de chave de API.

Atenção: a cobertura de pequenos negócios no OpenStreetMap depende de
voluntários mapearem a região — em cidades menores pode haver bem menos
resultados do que no Google Maps. Se a busca não trouxer nada, tente um
raio maior (o código usa 8km em torno do centro da cidade) ou cadastre
os leads manualmente com leads/import_manual.py.

As APIs públicas do OpenStreetMap (Nominatim e Overpass) são mantidas pela
comunidade: este script já respeita o limite de 1 requisição/segundo ao
Nominatim e identifica a aplicação via User-Agent, conforme as políticas de
uso. Evite rodar muitas buscas seguidas em pouco tempo.

Uso:
    python leads/find_leads_osm.py --cidade "Aracaju, SE" --tipo "hamburgueria" --max 20
"""

import argparse
import os
import sys
import time
import unicodedata

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import LEADS_CSV, SEU_NOME
from leads.find_leads import is_probable_whatsapp, phone_to_e164_br
from leads.lead_store import load_leads, save_leads, upsert_lead

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = f"site-automatico/1.0 (uso pessoal - {SEU_NOME})"

# Área OSM (relation/way) para id de área do Overpass, conforme a convenção
# https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL#By_area_id
AREA_OFFSET = {"relation": 3600000000, "way": 2400000000}

# Tipos de negócio comuns -> tags do OpenStreetMap. Se o tipo pedido não
# estiver aqui, cai no fallback por nome (busca o texto no campo "name").
TYPE_TAGS = {
    "hamburgueria": [("amenity", "fast_food")],
    "lanchonete": [("amenity", "fast_food")],
    "fast food": [("amenity", "fast_food")],
    "restaurante": [("amenity", "restaurant")],
    "pizzaria": [("amenity", "restaurant")],
    "padaria": [("shop", "bakery")],
    "confeitaria": [("shop", "confectionery")],
    "doceria": [("shop", "confectionery")],
    "sorveteria": [("amenity", "ice_cream")],
    "cafeteria": [("amenity", "cafe")],
    "cafe": [("amenity", "cafe")],
    "salao de beleza": [("shop", "hairdresser")],
    "cabeleireiro": [("shop", "hairdresser")],
    "barbearia": [("shop", "hairdresser")],
    "manicure": [("shop", "beauty")],
    "estetica": [("shop", "beauty")],
    "farmacia": [("amenity", "pharmacy")],
    "mercado": [("shop", "supermarket")],
    "mercadinho": [("shop", "convenience")],
    "petshop": [("shop", "pet")],
    "pet shop": [("shop", "pet")],
    "floricultura": [("shop", "florist")],
    "loja de roupas": [("shop", "clothes")],
    "boutique": [("shop", "clothes")],
    "academia": [("leisure", "fitness_centre")],
    "oficina mecanica": [("shop", "car_repair")],
    "auto pecas": [("shop", "car_parts")],
    "pousada": [("tourism", "guest_house")],
    "hotel": [("tourism", "hotel")],
    "papelaria": [("shop", "stationery")],
    "material de construcao": [("shop", "hardware")],
    "loja de celular": [("shop", "mobile_phone")],
    "otica": [("shop", "optician")],
}


def _normalize(texto):
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.strip().lower()


def geocode_cidade(cidade):
    query = cidade if "brasil" in cidade.lower() else f"{cidade}, Brasil"
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": query, "format": "jsonv2", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()
    resultados = resp.json()
    if not resultados:
        raise RuntimeError(f"Cidade não encontrada no OpenStreetMap: {cidade}")
    r = resultados[0]
    return {"osm_type": r["osm_type"], "osm_id": int(r["osm_id"]), "lat": float(r["lat"]), "lon": float(r["lon"])}


def _area_clause(geo):
    if geo["osm_type"] in AREA_OFFSET:
        area_id = AREA_OFFSET[geo["osm_type"]] + geo["osm_id"]
        return f"area({area_id})->.searchArea;\n", "(area.searchArea)"
    # Cidade sem contorno administrativo no OSM: busca num raio ao redor do centro
    return "", f'(around:8000,{geo["lat"]},{geo["lon"]})'


def build_overpass_query(tipo_negocio, geo):
    area_decl, area_suffix = _area_clause(geo)
    tag_filters = TYPE_TAGS.get(_normalize(tipo_negocio))

    if tag_filters:
        statements = [f'nwr["{chave}"="{valor}"]{area_suffix};' for chave, valor in tag_filters]
    else:
        termo = tipo_negocio.replace('"', "'")
        statements = [f'nwr[~"^(shop|amenity|craft|office|tourism|leisure)$"~"."]["name"~"{termo}",i]{area_suffix};']

    corpo = "\n  ".join(statements)
    return f"[out:json][timeout:60];\n{area_decl}(\n  {corpo}\n);\nout center tags;\n"


def run_overpass(query):
    resp = requests.post(OVERPASS_URL, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=90)
    resp.raise_for_status()
    return resp.json().get("elements", [])


def _endereco(tags, cidade_fallback):
    partes = []
    rua = tags.get("addr:street")
    numero = tags.get("addr:housenumber")
    if rua:
        partes.append(f"{rua}, {numero}" if numero else rua)
    bairro = tags.get("addr:suburb")
    if bairro:
        partes.append(bairro)
    cidade = tags.get("addr:city") or cidade_fallback
    if cidade:
        partes.append(cidade)
    return ", ".join(partes)


def find_leads_osm(cidade, tipo_negocio, max_results=20):
    print(f"Geocodificando '{cidade}' via Nominatim...")
    geo = geocode_cidade(cidade)
    time.sleep(1)  # cortesia com a política de uso do Nominatim (max 1 req/s)

    query = build_overpass_query(tipo_negocio, geo)
    print("Consultando Overpass API (OpenStreetMap)...")
    elementos = run_overpass(query)
    print(f"{len(elementos)} resultado(s) bruto(s). Filtrando sem site e com telefone tipo celular...")

    leads_by_id = load_leads(LEADS_CSV)
    novos = 0
    for el in elementos:
        if novos >= max_results:
            break
        tags = el.get("tags", {})
        nome = tags.get("name")
        if not nome:
            continue
        if tags.get("website") or tags.get("contact:website"):
            continue  # já tem site, não é lead

        telefone = tags.get("phone") or tags.get("contact:phone", "")
        e164 = phone_to_e164_br(telefone)
        if not is_probable_whatsapp(e164):
            continue

        centro = el.get("center", {})
        lat = el.get("lat", centro.get("lat", ""))
        lon = el.get("lon", centro.get("lon", ""))

        lead = {
            "place_id": f"osm:{el['type']}/{el['id']}",
            "source": "osm",
            "name": nome,
            "address": _endereco(tags, cidade),
            "city": cidade,
            "phone_e164": e164,
            "phone_display": telefone,
            "rating": "",
            "user_ratings_total": "",
            "maps_url": f"https://www.openstreetmap.org/{el['type']}/{el['id']}",
            "lat": lat,
            "lon": lon,
            "opening_hours_raw": tags.get("opening_hours", ""),
        }
        upsert_lead(leads_by_id, lead)
        novos += 1

    save_leads(LEADS_CSV, leads_by_id)
    print(f"{novos} lead(s) sem site adicionados/atualizados em {LEADS_CSV}")
    return novos


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cidade", required=True, help='Ex: "Aracaju, SE"')
    parser.add_argument("--tipo", required=True, help='Ex: "hamburgueria", "salão de beleza"')
    parser.add_argument("--max", type=int, default=20, dest="max_results")
    args = parser.parse_args()
    find_leads_osm(args.cidade, args.tipo, args.max_results)
