"""
Roda o funil completo: busca leads -> gera sites -> gera propostas prontas
para envio manual pelo WhatsApp.

Uso:
    python run_pipeline.py --cidade "Aracaju, SE" --tipo "hamburgueria" --max 20
    python run_pipeline.py --cidade "Aracaju, SE" --tipo "salão de beleza" --base-url https://meusite.netlify.app
"""

import argparse

from leads.find_leads import find_leads
from outreach.generate_proposals import generate_proposals
from site_generator.generate_site import generate_sites

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cidade", required=True, help='Ex: "Aracaju, SE"')
    parser.add_argument("--tipo", required=True, help='Ex: "hamburgueria", "salão de beleza"')
    parser.add_argument("--max", type=int, default=20, dest="max_results")
    parser.add_argument("--base-url", default=None, help="URL de deploy dos sites (opcional)")
    args = parser.parse_args()

    print("== Etapa 1/3: buscando leads ==")
    find_leads(args.cidade, args.tipo, args.max_results)

    print("\n== Etapa 2/3: gerando sites ==")
    generate_sites()

    print("\n== Etapa 3/3: gerando propostas ==")
    generate_proposals(base_url=args.base_url)

    print("\nPronto! Abra outreach/prontos_para_enviar.csv, revise as mensagens")
    print("e clique nos links wa.me para enviar manualmente pelo seu WhatsApp.")
