"""
Fallback sem nenhuma API: importa leads de um CSV simples que você mesmo
preenche (pesquisando manualmente no Google/Instagram/WhatsApp), no formato
de leads/leads_manual_exemplo.csv (colunas: nome,telefone,endereco,cidade).

Uso:
    python leads/import_manual.py --arquivo meus_leads.csv
"""

import argparse
import csv
import os
import sys

from slugify import slugify

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import LEADS_CSV
from leads.find_leads import is_probable_whatsapp, phone_to_e164_br
from leads.lead_store import load_leads, save_leads, upsert_lead


def import_manual(arquivo_csv):
    leads_by_id = load_leads(LEADS_CSV)
    importados = 0

    with open(arquivo_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        campos_esperados = {"nome", "telefone", "endereco", "cidade"}
        faltando = campos_esperados - set(reader.fieldnames or [])
        if faltando:
            raise SystemExit(f"Colunas faltando no CSV: {', '.join(sorted(faltando))}")

        for row in reader:
            nome = row["nome"].strip()
            if not nome:
                continue
            telefone = row["telefone"].strip()
            cidade = row["cidade"].strip()
            e164 = phone_to_e164_br(telefone)

            if not is_probable_whatsapp(e164):
                print(f"Aviso: número de '{nome}' não parece celular BR ({telefone}). Importado mesmo assim.")

            lead = {
                "place_id": f"manual:{slugify(nome + '-' + cidade)}",
                "source": "manual",
                "name": nome,
                "address": row["endereco"].strip(),
                "city": cidade,
                "phone_e164": e164,
                "phone_display": telefone,
                "rating": "",
                "user_ratings_total": "",
                "maps_url": "",
                "lat": "",
                "lon": "",
                "opening_hours_raw": "",
            }
            upsert_lead(leads_by_id, lead)
            importados += 1

    save_leads(LEADS_CSV, leads_by_id)
    print(f"{importados} lead(s) importado(s) em {LEADS_CSV}")
    return importados


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arquivo", required=True, help="CSV com colunas nome,telefone,endereco,cidade")
    args = parser.parse_args()
    import_manual(args.arquivo)
