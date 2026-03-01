#!/usr/bin/env python3
"""
DataEraser - Outil local de nettoyage de présence numérique
Lancer : python app.py  puis ouvrir http://localhost:5000
"""

from flask import Flask, jsonify, request, Response
import urllib.parse
from datetime import datetime
import os
import sys
from pathlib import Path

app = Flask(__name__)

def resource_path(rel):
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent
    return base / rel

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response

@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        return Response(status=204, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
        })

# ─────────────────────────────────────────────
#  TEMPLATES EMAILS RGPD
# ─────────────────────────────────────────────

def generer_email_rgpd(prenom, nom, email_contact, site, url_page=""):
    today = datetime.now().strftime("%d/%m/%Y")
    objet = f"Demande d'effacement de donnees personnelles - Article 17 RGPD - {prenom} {nom}"
    ref_url = f"\nURL concernee : {url_page}" if url_page else ""

    corps = f"""Madame, Monsieur,

Je me permets de vous contacter conformement au Reglement General sur la Protection des Donnees (RGPD - Reglement UE 2016/679), et plus particulierement en application de son Article 17 relatif au droit a l'effacement.

Des donnees personnelles me concernant apparaissent sur votre plateforme {site}.{ref_url}

Ces donnees incluent notamment mon nom et prenom, et potentiellement d'autres informations me concernant, collectees et diffusees sans mon consentement explicite.

En vertu de l'Article 17 SS1 du RGPD, je vous demande formellement :
  1. L'effacement immediat de l'integralite des donnees me concernant ;
  2. La confirmation ecrite de cet effacement dans un delai de trente (30) jours.

Mes coordonnees pour traitement :
  Nom complet : {prenom} {nom}
  Email de contact : {email_contact if email_contact else "[votre email]"}
  Date de la demande : {today}

En l'absence de reponse satisfaisante dans ce delai legal, je me verrai dans l'obligation de saisir la Commission Nationale de l'Informatique et des Libertes (CNIL) d'une plainte formelle (cnil.fr/fr/plaintes) et, le cas echeant, de faire valoir mes droits en justice.

Je reste a votre disposition pour toute question complementaire.

Cordialement,
{prenom} {nom}"""

    return {"objet": objet, "corps": corps, "site": site, "url_page": url_page}


# ─────────────────────────────────────────────
#  ROUTES API
# ─────────────────────────────────────────────

@app.route("/")
def index():
    path = resource_path("static/index.html")
    return path.read_text(encoding="utf-8")

@app.route('/shutdown', methods=['POST'])
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()
    os._exit(0)

@app.route("/api/search-variants", methods=["POST"])
def search_variants():
    data = request.json
    prenom     = data.get("prenom", "").strip()
    nom        = data.get("nom", "").strip()
    alt_prenom = data.get("alt_prenom", "").strip()
    alt_nom    = data.get("alt_nom", "").strip()
    ville      = data.get("ville", "").strip()
    pseudo     = data.get("pseudo", "").strip()
    modes      = data.get("modes", ["prenom_nom", "nom_prenom", "sans_guillemets"])

    if not prenom or not nom:
        return jsonify({"error": "Prenom et nom requis"}), 400

    base_queries = []
    if "prenom_nom" in modes:
        base_queries.append(f'"{prenom} {nom}"')
    if "nom_prenom" in modes:
        base_queries.append(f'"{nom} {prenom}"')
    if "sans_guillemets" in modes:
        base_queries.append(f'{prenom} {nom}')

    if not base_queries:
        base_queries = [f'"{prenom} {nom}"']

    variants = list(base_queries)
    if alt_prenom:
        if "prenom_nom" in modes:
            variants.append(f'"{alt_prenom} {nom}"')
        if "nom_prenom" in modes:
            variants.append(f'"{nom} {alt_prenom}"')
    if alt_nom:
        variants.append(f'"{prenom} {alt_nom}"')
    if ville:
        for q in base_queries:
            variants.append(f'{q} {ville}')
    if pseudo:
        variants.append(f'"{pseudo}"')
        variants.append(pseudo)

    name_q = urllib.parse.quote(f'{prenom} {nom}')

    def engine_links(url_tpl):
        return [{"variante": q, "url": url_tpl.format(q=urllib.parse.quote(q), name_q=name_q)}
                for q in base_queries]

    search_engines = [
        {"nom": "Google",        "type": "general",    "liens": engine_links("https://www.google.com/search?q={q}")},
        {"nom": "Bing",          "type": "general",    "liens": engine_links("https://www.bing.com/search?q={q}")},
        {"nom": "DuckDuckGo",    "type": "prive",      "liens": engine_links("https://duckduckgo.com/?q={q}")},
        {"nom": "Yahoo",         "type": "general",    "liens": engine_links("https://search.yahoo.com/search?p={q}")},
        {"nom": "Qwant",         "type": "europeen",   "liens": engine_links("https://www.qwant.com/?q={q}")},
        {"nom": "Ecosia",        "type": "ecolo",      "liens": engine_links("https://www.ecosia.org/search?q={q}")},
        {"nom": "Yandex",        "type": "russe",      "liens": engine_links("https://yandex.com/search/?text={q}")},
        {"nom": "Google Images", "type": "images",     "liens": engine_links("https://www.google.com/search?q={q}&tbm=isch")},
        {"nom": "Google News",   "type": "actualites", "liens": engine_links("https://news.google.com/search?q={q}")},
        {"nom": "LinkedIn",      "type": "pro",        "liens": engine_links("https://www.linkedin.com/search/results/people/?keywords={q}")},
        {"nom": "Twitter/X",     "type": "social",     "liens": engine_links("https://twitter.com/search?q={q}")},
        {"nom": "Facebook",      "type": "social",     "liens": [{"variante": f"{prenom} {nom}", "url": f"https://www.facebook.com/search/top?q={name_q}"}]},
        {"nom": "YouTube",       "type": "video",      "liens": engine_links("https://www.youtube.com/results?search_query={q}")},
        {"nom": "GitHub",        "type": "dev",        "liens": engine_links("https://github.com/search?q={q}&type=users")},
    ]

    fn_url   = urllib.parse.quote(prenom)
    ln_url   = urllib.parse.quote(nom)
    full_url = urllib.parse.quote(f"{prenom} {nom}")

    data_brokers = [
        {"nom": "Societe.com",      "desc": "Dirigeants et mandataires sociaux", "url": f"https://www.societe.com/cgi-bin/search?champs={full_url}"},
        {"nom": "Infogreffe",       "desc": "Registre du commerce officiel",     "url": f"https://www.infogreffe.fr/recherche-entreprise-dirigeant/resultats-de-recherche?recherche=Entreprises&dirigeantPage=0&dirigeantPageSize=10&phrase={ln_url}%20{fn_url}"},
        {"nom": "Geneanet",         "desc": "Donnees genealogiques publiques",   "url": f"https://www.geneanet.org/fonds/individus/?sexe=&nom={ln_url}&ignore_each_patronyme=&prenom={fn_url}&prenom_operateur=and&ignore_each_prenom=&place__0__=&zonegeo__0__=&country__0__=&region__0__=&subregion__0__=&place__1__=&zonegeo__1__=&country__1__=&region__1__=&subregion__1__=&place__2__=&zonegeo__2__=&country__2__=&region__2__=&subregion__2__=&place__3__=&zonegeo__3__=&country__3__=&region__3__=&subregion__3__=&place__4__=&zonegeo__4__=&country__4__=&region__4__=&subregion__4__=&type_periode=between&from=&to=&exact_day=&exact_month=&exact_year=&go=1"},
        {"nom": "Verif.com",        "desc": "Fiche personne / dirigeant",        "url": f"https://www.verif.com/searchResult/?search={fn_url}+{ln_url}&country=FR"},
    ]

    return jsonify({"variants": variants, "search_engines": search_engines, "data_brokers": data_brokers})


@app.route("/api/generer-emails", methods=["POST"])
def generer_emails():
    data          = request.json
    prenom        = data.get("prenom", "").strip()
    nom           = data.get("nom", "").strip()
    email_contact = data.get("email", "").strip()
    sites         = data.get("sites", [])

    if not prenom or not nom:
        return jsonify({"error": "Prenom et nom requis"}), 400
    if not sites:
        return jsonify({"error": "Aucun site fourni"}), 400

    emails = []
    for s in sites:
        site_nom = s.get("site", "").strip()
        url_page = s.get("url_page", "").strip()
        if site_nom:
            emails.append(generer_email_rgpd(prenom, nom, email_contact, site_nom, url_page))

    return jsonify({"emails": emails, "count": len(emails)})


@app.route("/api/deref-links", methods=["POST"])
def deref_links():
    data             = request.json
    prenom           = data.get("prenom", "")
    nom              = data.get("nom", "")
    urls_a_supprimer = data.get("urls", [])

    liens = [
        {"moteur": "Google",            "description": "Formulaire officiel RGPD - droit a l'oubli",   "url": "https://reportcontent.google.com/forms/rtbf",                                                                   "delai": "~30 jours",  "type": "formulaire"},
        {"moteur": "Bing / Microsoft",  "description": "Demande de suppression de contenu",             "url": "https://www.microsoft.com/en-us/concern/bing",                                                                 "delai": "~30 jours",  "type": "formulaire"},
        {"moteur": "Google - URL",      "description": "Retirer une URL precise des resultats",         "url": "https://search.google.com/search-console/remove-outdated-content",                                             "delai": "~24h-7j",    "type": "outil"},
        {"moteur": "DuckDuckGo",        "description": "Email au DPO",                                  "url": "https://duckduckgo.com/duckduckgo-help-pages/legal/gdpr/",  "email": "dpo@duckduckgo.com",                     "delai": "~30 jours",  "type": "email"},
        {"moteur": "Qwant",             "description": "Demande RGPD Qwant",                            "url": "https://www.qwant.com/fr/rgpd",                             "email": "rgpd@qwant.com",                         "delai": "~30 jours",  "type": "email"},
        {"moteur": "Yahoo",             "description": "Centre d'aide - suppression",                   "url": "https://help.yahoo.com/kb/SLN28891.html",                                                                      "delai": "~30 jours",  "type": "formulaire"},
        {"moteur": "Wayback Machine",   "description": "Supprimer des archives web",                    "url": "https://help.archive.org/help/how-do-i-request-to-have-something-removed-from-the-wayback-machine/",           "delai": "Variable",   "type": "formulaire"},
        {"moteur": "CNIL - Plainte",    "description": "Recours si pas de reponse apres 30 jours",     "url": "https://www.cnil.fr/fr/plaintes",                                                                              "delai": "Legal",      "type": "autorite"},
    ]

    return jsonify({"liens": liens, "email_deref": generer_email_deref(prenom, nom, urls_a_supprimer)})


def generer_email_deref(prenom, nom, urls=[]):
    today      = datetime.now().strftime("%d/%m/%Y")
    liste_urls = "\n".join([f"  - {u}" for u in urls]) if urls else "  [Indiquer les URLs concernees]"
    return f"""Objet : Demande de dereferencement - Article 17 RGPD - {prenom} {nom}

Madame, Monsieur,

Je vous contacte conformement au Reglement General sur la Protection des Donnees (RGPD - UE 2016/679), Article 17, afin de solliciter le dereferencement de pages affichant des donnees personnelles me concernant dans vos resultats de recherche.

URLs a dereferencement :
{liste_urls}

Motifs (Art. 17 SS1) :
  - Ces donnees ne sont plus necessaires au regard des finalites pour lesquelles elles ont ete collectees ;
  - Je m'oppose au traitement de ces donnees (Art. 21 RGPD) ;
  - Ces informations portent atteinte a ma vie privee.

Identite : {prenom} {nom}
Date : {today}

Je vous rappelle votre obligation de repondre dans un delai de trente (30) jours. Sans reponse satisfaisante, je saisirai la CNIL (cnil.fr/fr/plaintes).

Cordialement,
{prenom} {nom}"""


@app.route("/api/extra-tools", methods=["GET"])
def extra_tools():
    return jsonify([
        {"nom": "Google Alerts",   "desc": "Surveillance temps reel de votre nom",  "url": "https://www.google.com/alerts",                    "categorie": "surveillance"},
        {"nom": "Have I Been Pwned","desc": "Fuites de donnees par email",           "url": "https://haveibeenpwned.com",                       "categorie": "fuites"},
        {"nom": "JustDeleteMe",    "desc": "Liens directs pour supprimer vos comptes","url": "https://justdeleteme.xyz/fr",                     "categorie": "comptes"},
        {"nom": "AccountKiller",   "desc": "Guides suppression de comptes",          "url": "https://www.accountkiller.com/fr",                 "categorie": "comptes"},
        {"nom": "Deseat.me",       "desc": "Trouve tous vos comptes via Gmail",      "url": "https://www.deseat.me/",                          "categorie": "comptes"},
        {"nom": "Namecheckr",      "desc": "Votre nom sur 100+ plateformes",         "url": "https://www.namecheckr.com/",                     "categorie": "surveillance"},
        {"nom": "Privacy Bee",     "desc": "Opt-out data brokers automatique",       "url": "https://privacybee.com/",                         "categorie": "data-brokers"},
        {"nom": "Browserleaks",    "desc": "Ce que votre navigateur revele",         "url": "https://browserleaks.com/",                       "categorie": "technique"},
        {"nom": "Sherlock",        "desc": "OSINT username sur 300+ sites",          "url": "https://github.com/sherlock-project/sherlock",     "categorie": "technique"},
    ])


if __name__ == "__main__":
    import webbrowser, threading, time
    def open_browser():
        time.sleep(1.3)
        webbrowser.open("http://localhost:5000")
    threading.Thread(target=open_browser, daemon=True).start()
    print("\n" + "="*50)
    print("  DataEraser")
    print("="*50)
    print("  Ouverture auto du navigateur...")
    print("  ou : http://localhost:5000")
    print("  Ctrl+C pour arreter")
    print("="*50 + "\n")
    app.run(debug=False, port=5000, host="127.0.0.1")
