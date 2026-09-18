"""
Gera um site estático simples (uma página) para cada lead com status "novo",
usando os dados coletados (Google Places, OpenStreetMap ou cadastro manual).

Uso:
    python site_generator/generate_site.py
    python site_generator/generate_site.py --place-id ChIJ...
"""

import argparse
import os
import sys

from jinja2 import Environment, FileSystemLoader
from slugify import slugify

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GOOGLE_PLACES_API_KEY, LEADS_CSV, PRECO_SITE, SEU_NOME, SEU_WHATSAPP, SITES_DIR
from leads.find_leads import get_place_details
from leads.lead_store import load_leads, save_leads

TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))


def _whatsapp_link(e164_digits, texto=""):
    if not e164_digits:
        return ""
    link = f"https://wa.me/{e164_digits}"
    if texto:
        from urllib.parse import quote

        link += f"?text={quote(texto)}"
    return link


def _osm_embed_src(lat, lon, delta=0.003):
    lat, lon = float(lat), float(lon)
    bbox = f"{lon - delta},{lat - delta},{lon + delta},{lat + delta}"
    return f"https://www.openstreetmap.org/export/embed.html?bbox={bbox}&marker={lat},{lon}"


def generate_site_for_lead(lead):
    place_id = lead["place_id"]
    is_google_place = GOOGLE_PLACES_API_KEY and not place_id.startswith(("osm:", "manual:"))

    opening_hours = []
    maps_embed_src = ""

    if is_google_place:
        details = get_place_details(place_id) or {}
        opening_hours = details.get("opening_hours", {}).get("weekday_text", [])
        maps_embed_src = f"https://www.google.com/maps/embed/v1/place?key={GOOGLE_PLACES_API_KEY}&q=place_id:{place_id}"
    else:
        # Lead veio do OpenStreetMap (ou de cadastro manual): usa os dados
        # já coletados no leads.csv, sem depender de nenhuma chave de API.
        if lead.get("opening_hours_raw"):
            opening_hours = [h.strip() for h in lead["opening_hours_raw"].split(";") if h.strip()]
        if lead.get("lat") and lead.get("lon"):
            maps_embed_src = _osm_embed_src(lead["lat"], lead["lon"])

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("template.html")

    html = template.render(
        name=lead["name"],
        address=lead.get("address", ""),
        phone_display=lead.get("phone_display", ""),
        rating=lead.get("rating", ""),
        user_ratings_total=lead.get("user_ratings_total", ""),
        opening_hours=opening_hours,
        cardapio_items=[],  # preencher manualmente depois, se o negócio enviar o cardápio
        whatsapp_link=_whatsapp_link(lead.get("phone_e164", "")),
        maps_embed_src=maps_embed_src,
        seu_nome=SEU_NOME,
        preco=PRECO_SITE,
        seu_whatsapp_link=_whatsapp_link(SEU_WHATSAPP, f"Oi! Vi o site de demonstração de {lead['name']}."),
    )

    slug = slugify(f"{lead['name']}-{lead.get('city', '')}")
    site_dir = os.path.join(SITES_DIR, slug)
    os.makedirs(site_dir, exist_ok=True)
    site_path = os.path.join(site_dir, "index.html")
    with open(site_path, "w", encoding="utf-8") as f:
        f.write(html)

    return slug, site_path


def generate_sites(only_place_id=None):
    leads_by_id = load_leads(LEADS_CSV)
    if not leads_by_id:
        print(f"Nenhum lead encontrado em {LEADS_CSV}. Rode find_leads.py primeiro.")
        return

    alvo = leads_by_id.values() if not only_place_id else [leads_by_id[only_place_id]]
    gerados = 0
    for lead in alvo:
        if not only_place_id and lead.get("status") != "novo":
            continue
        slug, site_path = generate_site_for_lead(lead)
        lead["site_slug"] = slug
        lead["site_path"] = site_path
        lead["status"] = "site_gerado"
        gerados += 1
        print(f"Site gerado: {site_path}")

    save_leads(LEADS_CSV, leads_by_id)
    print(f"{gerados} site(s) gerado(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--place-id", default=None, help="Gerar site apenas para este place_id")
    args = parser.parse_args()
    generate_sites(only_place_id=args.place_id)
