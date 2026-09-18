# site-automatico

Ferramenta para prospectar pequenos negócios brasileiros sem site (hamburguerias,
salões, lojas etc.), gerar automaticamente um site de demonstração com as
informações deles, e preparar uma proposta comercial (R$ 100 pelo site) para
você enviar pelo seu próprio WhatsApp.

## Como funciona (funil)

1. **Buscar leads** — três opções, sem precisar escolher só uma:
   - `leads/find_leads_osm.py` **(padrão, sem chave de API)**: usa o
     OpenStreetMap (Nominatim + Overpass), gratuito e sem cadastro.
   - `leads/find_leads.py`: usa o Google Places (mais completo, mas exige
     `GOOGLE_PLACES_API_KEY`).
   - `leads/import_manual.py`: você mesmo cola os leads num CSV simples
     (nome, telefone, endereço, cidade) — zero API.

   Qualquer uma das três filtra apenas negócios **sem site cadastrado** e
   com telefone com cara de celular (candidato a WhatsApp), salvando em
   `leads/leads.csv`.
2. **Gerar site** (`site_generator/generate_site.py`): cria uma página HTML
   simples (`sites/<slug>/index.html`) com nome, endereço, telefone, avaliação,
   horário de funcionamento e mapa — pronta para visualizar ou publicar.
3. **Gerar proposta** (`outreach/generate_proposals.py`): monta a mensagem de
   venda personalizada e um link `wa.me` já com o texto preenchido, apontando
   para o WhatsApp **do negócio**. Tudo fica em
   `outreach/prontos_para_enviar.csv`.
4. **Você envia manualmente**: abre o CSV, revisa cada mensagem e clica no
   link para enviar pelo seu WhatsApp (79998942945). Nada é enviado sozinho.
5. **Acompanhar respostas** (`crm/update_status.py`): quando alguém responder
   interessado, marque o status — isso é o seu lembrete pra entrar em contato
   pessoalmente e fechar o negócio.

Rodar tudo de uma vez (por padrão usa OpenStreetMap, sem chave nenhuma):

```bash
python run_pipeline.py --cidade "Aracaju, SE" --tipo "hamburgueria" --max 20

# ou, se tiver a chave do Google:
python run_pipeline.py --cidade "Aracaju, SE" --tipo "hamburgueria" --fonte google
```

## Por que o envio é manual (não 100% automático)

Ferramentas não-oficiais de automação do WhatsApp (ex: whatsapp-web.js,
Baileys) para disparo em massa **violam os Termos de Uso do WhatsApp** e podem
banir seu número rapidamente — principalmente por denúncias de spam de quem
nunca falou com você antes. Como isso derrubaria a operação inteira (e seu
WhatsApp pessoal junto), o pipeline monta tudo pronto (site + mensagem +
link), mas quem clica em "enviar" é você. Isso também te dá controle pra
ajustar o tom da mensagem lead a lead.

Se no futuro você quiser automação de envio de verdade e escalável, o caminho
correto é a **API oficial do WhatsApp Business** (via Meta, Twilio ou
360dialog), que exige cadastro de empresa e aprovação de templates, mas não
tem risco de banimento.

## Fontes de leads sem chave de API do Google

**OpenStreetMap (`find_leads_osm.py`, padrão do `run_pipeline.py`)**: não
precisa de cadastro nem chave. Usa duas APIs públicas mantidas pela
comunidade:
- Nominatim, para converter o nome da cidade em coordenadas;
- Overpass API, para buscar os negócios por categoria dentro da cidade.

O script já respeita as políticas de uso dessas APIs públicas (identifica a
aplicação via User-Agent e espaça as requisições). A limitação real é a
**cobertura de dados**: como o OpenStreetMap é mantido por voluntários,
cidades grandes costumam ter bastante coisa mapeada, mas cidades pequenas
podem retornar poucos ou nenhum resultado — nesse caso, use o cadastro
manual abaixo.

O gerador de site (`generate_site.py`) também funciona 100% sem chave nesse
caso: usa o mapa embutido gratuito do OpenStreetMap e o horário de
funcionamento que já veio na busca.

**Cadastro manual (`import_manual.py`)**: zero API, zero dependência
externa. Copie `leads/leads_manual_exemplo.csv`, preencha com os negócios que
você mesmo encontrou (WhatsApp aberto, Instagram, indicação, etc.) e rode:

```bash
python leads/import_manual.py --arquivo meus_leads.csv
python site_generator/generate_site.py
python outreach/generate_proposals.py
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite `.env` (todos os campos têm valor padrão, exceto a chave do Google):

- `GOOGLE_PLACES_API_KEY`: **opcional**, só necessária se você quiser usar
  `--fonte google` em vez do OpenStreetMap. Crie em
  https://console.cloud.google.com/, ative a **Places API** (e **Maps Embed
  API** se quiser o mapa do Google no site), gere uma chave e **restrinja por
  IP ou referrer** antes de usar em produção. O Google cobra por consulta
  acima da cota gratuita mensal — confira os preços atuais no console antes
  de rodar buscas grandes.
- `SEU_WHATSAPP`: seu número no formato `55DDDNUMERO` (já vem preenchido com
  `5579998942945`).
- `SEU_NOME`: nome que aparece na proposta e no rodapé dos sites.
- `PRECO_SITE`: valor cobrado (usado só no texto da mensagem).

## Uso passo a passo

```bash
# 1. Buscar leads sem site em uma cidade/categoria (OpenStreetMap, sem chave)
python leads/find_leads_osm.py --cidade "Aracaju, SE" --tipo "hamburgueria" --max 20

# (alternativa com Google, exige GOOGLE_PLACES_API_KEY no .env)
# python leads/find_leads.py --cidade "Aracaju, SE" --tipo "hamburgueria" --max 20

# (alternativa 100% manual, sem nenhuma API)
# python leads/import_manual.py --arquivo meus_leads.csv

# 2. Gerar os sites de demonstração
python site_generator/generate_site.py

# 3. Gerar as propostas (links wa.me prontos)
python outreach/generate_proposals.py --base-url https://seusite.netlify.app

# 4. Abrir outreach/prontos_para_enviar.csv, revisar e clicar nos links para enviar

# 5. Quando alguém responder, marcar o status
python crm/update_status.py --listar
python crm/update_status.py <place_id> interessado
```

Sem `--base-url`, o CSV aponta para o arquivo local gerado (`sites/<slug>/index.html`)
— publique onde preferir (GitHub Pages, Netlify, Vercel, etc.) e rode o passo 3
de novo com a URL real antes de enviar.

## Avisos importantes

- **Dados pessoais (LGPD)**: `leads/leads.csv` guarda nome e telefone de
  pessoas/negócios reais — por isso já está no `.gitignore` e não deve ser
  publicado ou compartilhado. Apague os dados de quem pedir para não ser mais
  contatado.
- **Mensagem comercial não solicitada**: mesmo enviando manualmente, é uma
  abordagem fria (cold outreach). Identifique-se claramente, seja transparente
  sobre ser uma oferta paga, e pare de contatar quem responder que não tem
  interesse.
- **Cardápio e fotos**: nenhuma das fontes (Google, OSM ou manual) retorna
  cardápio. O site gerado mostra um aviso "cardápio em breve" com botão de
  WhatsApp — depois que o negócio topar, peça as informações reais (cardápio,
  fotos, texto) para completar o site antes da entrega final.
- **Custo/limite das APIs**: com `--fonte osm` não há custo, mas evite rodar
  muitas buscas seguidas em pouco tempo (é infraestrutura pública mantida pela
  comunidade). Com `--fonte google`, cada busca consome cota do Google
  Places — ajuste `--max` para controlar quantos lugares são verificados por
  execução.
