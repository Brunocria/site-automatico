"""
Atualiza manualmente o status de um lead depois que você conversou com o
negócio pelo WhatsApp. Use isto para acompanhar o funil.

Status sugeridos: novo, site_gerado, proposta_pronta, proposta_enviada,
interessado, fechado, recusado.

Uso:
    python crm/update_status.py ChIJ... interessado
    python crm/update_status.py --listar
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import LEADS_CSV
from leads.lead_store import load_leads, save_leads

STATUS_VALIDOS = {
    "novo",
    "site_gerado",
    "proposta_pronta",
    "proposta_enviada",
    "interessado",
    "fechado",
    "recusado",
}


def listar(leads_by_id):
    for lead in leads_by_id.values():
        print(f"{lead['place_id']}  [{lead.get('status', '')}]  {lead.get('name', '')}  ({lead.get('phone_display', '')})")


def update_status(place_id, novo_status):
    if novo_status not in STATUS_VALIDOS:
        raise SystemExit(f"Status inválido: {novo_status}. Use um de: {', '.join(sorted(STATUS_VALIDOS))}")

    leads_by_id = load_leads(LEADS_CSV)
    if place_id not in leads_by_id:
        raise SystemExit(f"place_id não encontrado em {LEADS_CSV}")

    leads_by_id[place_id]["status"] = novo_status
    save_leads(LEADS_CSV, leads_by_id)
    nome = leads_by_id[place_id].get("name", "")
    print(f"{nome} -> status atualizado para '{novo_status}'")
    if novo_status == "interessado":
        print(f"Lembrete: entre em contato pessoalmente com {nome} para fechar o site.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("place_id", nargs="?", help="place_id do lead (veja leads/leads.csv)")
    parser.add_argument("status", nargs="?", help="novo status")
    parser.add_argument("--listar", action="store_true", help="lista todos os leads e seus status")
    args = parser.parse_args()

    if args.listar:
        listar(load_leads(LEADS_CSV))
    elif args.place_id and args.status:
        update_status(args.place_id, args.status)
    else:
        parser.print_help()
