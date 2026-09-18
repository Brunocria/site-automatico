import os

from dotenv import load_dotenv

load_dotenv()

GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
SEU_WHATSAPP = os.environ.get("SEU_WHATSAPP", "5579998942945")
SEU_NOME = os.environ.get("SEU_NOME", "Seu Nome")
PRECO_SITE = os.environ.get("PRECO_SITE", "100")

LEADS_CSV = os.path.join(os.path.dirname(__file__), "leads", "leads.csv")
SITES_DIR = os.path.join(os.path.dirname(__file__), "sites")
PROPOSALS_CSV = os.path.join(os.path.dirname(__file__), "outreach", "prontos_para_enviar.csv")
