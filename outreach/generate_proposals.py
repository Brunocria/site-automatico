"""
Monta a mensagem de proposta para cada lead com status "site_gerado" e gera
um link wa.me pronto, com o texto já preenchido, para o WhatsApp DO NEGÓCIO
(não do seu). Nada é enviado automaticamente — você abre o link e clica em
"Enviar" manualmente pelo seu WhatsApp (79998942945), como combinado.

Uso:
    python outreach/generate_proposals.py
    python outreach/generate_proposals.py --base-url https://meusite.netlify.app
"""

import argparse
import csv
import os
import sys
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import LEADS_CSV, PRECO_SITE, PROPOSALS_CSV, SEU_NOME
from leads.lead_store import load_leads, save_leads

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "message_template.txt")


def _site_link(lead, base_url):
    if base_url:
        return f"{base_url.rstrip('/')}/{lead['site_slug']}/"
    # Sem deploy configurado: aponta para o arquivo local gerado, para você
    # visualizar e decidir como hospedar (GitHub Pages, Netlify, etc.).
    return f"arquivo local: {lead.get('site_path', '(gerar site primeiro)')}"


def generate_proposals(base_url=None):
    leads_by_id = load_leads(LEADS_CSV)
    if not leads_by_id:
        print(f"Nenhum lead encontrado em {LEADS_CSV}.")
        return

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()

    linhas = []
    prontos = 0
    for lead in leads_by_id.values():
        if lead.get("status") != "site_gerado":
            continue

        mensagem = template.format(
            seu_nome=SEU_NOME,
            nome_negocio=lead["name"],
            link_site=_site_link(lead, base_url),
            preco=PRECO_SITE,
        )
        wa_link = f"https://wa.me/{lead['phone_e164']}?text={quote(mensagem)}"

        linhas.append(
            {
                "name": lead["name"],
                "phone_display": lead.get("phone_display", ""),
                "link_para_enviar": wa_link,
                "mensagem": mensagem,
            }
        )
        lead["status"] = "proposta_pronta"
        prontos += 1

    save_leads(LEADS_CSV, leads_by_id)

    os.makedirs(os.path.dirname(PROPOSALS_CSV), exist_ok=True)
    with open(PROPOSALS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "phone_display", "link_para_enviar", "mensagem"])
        writer.writeheader()
        writer.writerows(linhas)

    print(f"{prontos} proposta(s) pronta(s) em {PROPOSALS_CSV}")
    print("Abra o CSV, revise cada mensagem e clique nos links para enviar manualmente pelo seu WhatsApp.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=None,
        help="URL onde os sites gerados estão publicados (ex: https://meusite.netlify.app). "
        "Se omitido, o CSV aponta para o arquivo local.",
    )
    args = parser.parse_args()
    generate_proposals(base_url=args.base_url)
