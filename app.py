#!/usr/bin/env python3
"""
DataEraser - Outil local de nettoyage de présence numérique
"""

from flask import Flask, jsonify, request, Response
import urllib.parse
import threading
from datetime import datetime
import os
import sys

app = Flask(__name__)

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

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

@app.route("/")
def index():
    path = resource_path(os.path.join("static", "index.html"))
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@app.route("/api/search-variants", methods=["POST"])
def search_variants():
    data       = request.json
    prenom     = data.get("prenom", "").strip()
    nom        = data.get("nom", "").strip()
    alt_prenom = data.get("alt_prenom", "").strip()
    alt_nom    = data.get("alt_nom", "").strip()
    ville      = data.get("ville", "").strip()
    pseudo     = data.get("pseudo", "").strip()
    telephone  = data.get("telephone", "").strip()
    modes      = data.get("modes", ["prenom_nom", "nom_prenom", "sans_guillemets"])

    if not prenom or not nom:
        return jsonify({"error": "Prenom et nom requis"}), 400

    # ── Construire les requêtes de base ──
    base_queries = []
    if "prenom_nom" in modes:
        base_queries.append(f'"{prenom} {nom}"')
    if "nom_prenom" in modes:
        base_queries.append(f'"{nom} {prenom}"')
    if "sans_guillemets" in modes:
        base_queries.append(f'{prenom} {nom}')
    if not base_queries:
        base_queries = [f'"{prenom} {nom}"']

    # ── Variantes enrichies ──
    variants = list(base_queries)

    alt_prenom_queries = []
    if alt_prenom:
        if "prenom_nom" in modes:
            q = f'"{alt_prenom} {nom}"'
            variants.append(q); alt_prenom_queries.append(q)
        if "nom_prenom" in modes:
            q = f'"{nom} {alt_prenom}"'
            variants.append(q); alt_prenom_queries.append(q)

    alt_nom_queries = []
    if alt_nom:
        q = f'"{prenom} {alt_nom}"'
        variants.append(q); alt_nom_queries.append(q)
        if alt_prenom:
            q2 = f'"{alt_prenom} {alt_nom}"'
            variants.append(q2); alt_nom_queries.append(q2)

    ville_queries = []
    if ville:
        for q in base_queries:
            vq = f'{q} {ville}'
            variants.append(vq); ville_queries.append(vq)
        for q in alt_prenom_queries:
            vq = f'{q} {ville}'
            variants.append(vq); ville_queries.append(vq)

    pseudo_queries = []
    if pseudo:
        variants.append(f'"{pseudo}"')
        variants.append(pseudo)
        pseudo_queries = [f'"{pseudo}"', pseudo]
        if ville:
            vq = f'"{pseudo}" {ville}'
            variants.append(vq); pseudo_queries.append(vq)

    # ── Variantes téléphone ──
    tel_clean  = ""
    tel_spaced = ""
    tel_dot    = ""
    phone_queries = []
    if telephone:
        tel_clean  = telephone.replace(" ", "").replace("-", "").replace(".", "")
        tel_spaced = " ".join([tel_clean[i:i+2] for i in range(0, len(tel_clean), 2)])
        tel_dot    = ".".join([tel_clean[i:i+2] for i in range(0, len(tel_clean), 2)])
        phone_queries = [
            f'"{telephone}"',
            f'"{tel_clean}"',
            f'"{tel_spaced}"',
            f'"{tel_dot}"',
            f'"{prenom} {nom}" {tel_clean}',
        ]
        for pq in phone_queries:
            if pq not in variants:
                variants.append(pq)

    name_q = urllib.parse.quote(f'{prenom} {nom}')

    def all_queries():
        seen = set(); result = []
        for q in base_queries + alt_prenom_queries + alt_nom_queries + ville_queries + pseudo_queries:
            if q not in seen:
                seen.add(q); result.append(q)
        return result

    def engine_links(url_tpl, queries=None):
        if queries is None:
            queries = all_queries()
        seen = set(); result = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                result.append({"variante": q, "url": url_tpl.format(q=urllib.parse.quote(q), name_q=name_q)})
        return result

    # Facebook : variantes simples uniquement (pas les guillemets, FB ne les gère pas)
    fb_queries = []
    fb_seen = set()
    for q in [f'{prenom} {nom}', f'{nom} {prenom}']:
        if q not in fb_seen:
            fb_seen.add(q); fb_queries.append(q)
    if alt_prenom:
        q = f'{alt_prenom} {nom}'
        if q not in fb_seen:
            fb_seen.add(q); fb_queries.append(q)
    if pseudo and pseudo not in fb_seen:
        fb_seen.add(pseudo); fb_queries.append(pseudo)

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
        {"nom": "Twitter / X",   "type": "social",     "liens": engine_links("https://x.com/search?q={q}&src=typed_query")},
        {"nom": "Instagram",     "type": "social",     "liens": (
            ([{"variante": f"@{pseudo} (profil direct)", "url": f"https://www.instagram.com/{urllib.parse.quote(pseudo)}/"}] if pseudo else []) +
            engine_links("https://www.instagram.com/explore/search/keyword/?q={q}", base_queries)
        )},
        {"nom": "Facebook",      "type": "social",     "liens": [{"variante": q, "url": f"https://www.facebook.com/search/people/?q={urllib.parse.quote(q)}"} for q in fb_queries]},
        {"nom": "TikTok",        "type": "social",     "liens": (
            ([{"variante": f"@{pseudo} (profil direct)", "url": f"https://www.tiktok.com/@{urllib.parse.quote(pseudo)}"}] if pseudo else []) +
            engine_links("https://www.tiktok.com/search?q={q}", base_queries)
        )},
        {"nom": "YouTube",       "type": "video",      "liens": engine_links("https://www.youtube.com/results?search_query={q}")},
        {"nom": "GitHub",        "type": "dev",        "liens": engine_links("https://github.com/search?q={q}&type=users")},
        {"nom": "Snapchat",      "type": "social",     "liens": (
            ([{"variante": f"@{pseudo} (profil direct)", "url": f"https://www.snapchat.com/add/{urllib.parse.quote(pseudo)}"}] if pseudo else []) +
            engine_links("https://www.google.com/search?q=site:snapchat.com+{q}", base_queries)
        )},
    ]

    # ── Section téléphone si renseigné ──
    if telephone and tel_clean:
        plinks = [{"variante": pq, "url": url.format(q=urllib.parse.quote(pq), name_q=name_q)}
                  for pq in phone_queries[:3]
                  for url in ["https://www.google.com/search?q={q}"]]
        search_engines += [
            {"nom": "Google (téléphone)",  "type": "telephone", "liens": [{"variante": pq, "url": f"https://www.google.com/search?q={urllib.parse.quote(pq)}"} for pq in phone_queries[:3]]},
            {"nom": "Bing (téléphone)",    "type": "telephone", "liens": [{"variante": pq, "url": f"https://www.bing.com/search?q={urllib.parse.quote(pq)}"} for pq in phone_queries[:3]]},
        ]

    fn_url   = urllib.parse.quote(prenom)
    ln_url   = urllib.parse.quote(nom)
    full_url = urllib.parse.quote(f"{prenom} {nom}")

    data_brokers = [
        {"nom": "Societe.com",  "desc": "Dirigeants et mandataires sociaux", "url": f"https://www.societe.com/cgi-bin/search?champs={full_url}"},
        {"nom": "Infogreffe",   "desc": "Registre du commerce officiel",     "url": f"https://www.infogreffe.fr/recherche-entreprise-dirigeant/resultats-de-recherche?recherche=Entreprises&dirigeantPage=0&dirigeantPageSize=10&phrase={ln_url}%20{fn_url}"},
        {"nom": "Geneanet",     "desc": "Données généalogiques publiques",   "url": f"https://www.geneanet.org/fonds/individus/?nom={ln_url}&prenom={fn_url}&go=1"},
        {"nom": "Verif.com",    "desc": "Fiche personne / dirigeant",        "url": f"https://www.verif.com/searchResult/?search={fn_url}+{ln_url}&country=FR"},
        {"nom": "PagesJaunes",  "desc": "Annuaire particuliers & pros",      "url": f"https://www.pagesjaunes.fr/pagesblanches/recherche?quoiqui={full_url}"},
    ]

    # ── Infos traitement données par RS ──
    rs_info = [
        {
            "nom": "Google / YouTube", "couleur": "#4285F4",
            "collecte": ["Recherches & historique", "Localisation GPS", "Emails & agenda", "Vidéos regardées", "Comportement cross-site"],
            "conservation": "Jusqu'à suppression du compte (18 mois pour certaines données d'activité)",
            "partage": "Annonceurs Google Ads, partenaires, services Google internes",
            "note": "Le 'Contrôle des données' dans les paramètres du compte permet de limiter la collecte."
        },
        {
            "nom": "Facebook / Meta", "couleur": "#1877F2",
            "collecte": ["Profil & réseau", "Localisation", "Messages (analyse IA)", "Contacts importés", "Comportement hors Facebook (Pixel Meta)"],
            "conservation": "90 jours après suppression du compte pour la plupart des données",
            "partage": "Annonceurs Meta, Instagram, WhatsApp, partenaires tiers",
            "note": "⚠ Le Pixel Meta collecte vos données sur des sites tiers même sans compte Facebook."
        },
        {
            "nom": "Instagram / Meta", "couleur": "#E1306C",
            "collecte": ["Photos & métadonnées", "Localisation GPS", "Contacts", "Données biométriques (visages)", "Comportement de navigation"],
            "conservation": "90 jours après suppression (données Meta partagées peuvent durer plus longtemps)",
            "partage": "Meta Ads, Facebook, partenaires tiers",
            "note": "La reconnaissance faciale automatique des photos est active par défaut."
        },
        {
            "nom": "X / Twitter", "couleur": "#1DA1F2",
            "collecte": ["Tweets publics indexés", "DM (analyse algorithmique)", "Localisation", "Contacts", "Cookies tiers"],
            "conservation": "30 jours après désactivation, jusqu'à 18 mois pour certaines données",
            "partage": "Annonceurs, partenaires de données, API publique",
            "note": "Les tweets publics sont indexés par tous les moteurs. Un compte privé ne protège pas les anciens tweets."
        },
        {
            "nom": "TikTok / ByteDance", "couleur": "#fe2c55",
            "collecte": ["Vidéos visionnées", "Localisation", "Contacts", "Voix & visage", "Presse-papiers", "Données biométriques"],
            "conservation": "Jusqu'à 30 jours après suppression (données analytiques : durée indéterminée)",
            "partage": "ByteDance (siège en Chine), annonceurs, partenaires",
            "note": "⚠ Données potentiellement accessibles par ByteDance en Chine. Interdit sur appareils gouvernementaux dans plusieurs pays."
        },
        {
            "nom": "LinkedIn / Microsoft", "couleur": "#0A66C2",
            "collecte": ["CV & réseau professionnel", "Activité & messages", "Comportement hors LinkedIn", "Données d'entreprise"],
            "conservation": "Jusqu'à suppression + 30 jours (certaines données archivées plus longtemps)",
            "partage": "Recruteurs, annonceurs B2B, Microsoft, partenaires",
            "note": "Votre profil public est indexé par Google même sans compte LinkedIn."
        },
        {
            "nom": "Snapchat", "couleur": "#FFFC00",
            "collecte": ["Snaps (temporairement)", "Localisation précise (Snap Map)", "Contacts", "Données de caméra"],
            "conservation": "Snaps non ouverts : 30j. Stories : 24h. Données compte : jusqu'à suppression.",
            "partage": "Snap Inc., annonceurs, partenaires analytiques",
            "note": "La Snap Map révèle votre position en temps réel à vos contacts si activée."
        },
    ]

    return jsonify({
        "variants": variants,
        "search_engines": search_engines,
        "data_brokers": data_brokers,
        "rs_info": rs_info,
        "has_phone": bool(telephone),
        "has_pseudo": bool(pseudo),
        "has_ville": bool(ville),
    })


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
        {"moteur": "Google",           "description": "Formulaire officiel RGPD - droit à l'oubli", "url": "https://reportcontent.google.com/forms/rtbf",                                  "delai": "~30 jours", "type": "formulaire"},
        {"moteur": "Bing / Microsoft", "description": "Demande de suppression de contenu",           "url": "https://www.microsoft.com/en-us/concern/bing",                                 "delai": "~30 jours", "type": "formulaire"},
        {"moteur": "Google - URL",     "description": "Retirer une URL précise des résultats",       "url": "https://search.google.com/search-console/remove-outdated-content",             "delai": "~24h-7j",   "type": "outil"},
        {"moteur": "DuckDuckGo",       "description": "Page d'aide déréférencement",                 "url": "https://duckduckgo.com/duckduckgo-help-pages/results/can-a-result-be-removed", "delai": "~30 jours", "type": "email"},
        {"moteur": "Yahoo",            "description": "Centre d'aide - suppression",                 "url": "https://fr.aide.yahoo.com/kb/SLN28252.html",                                   "delai": "~30 jours", "type": "formulaire"},
        {"moteur": "CNIL - Plainte",   "description": "Recours si pas de réponse après 30 jours",   "url": "https://www.cnil.fr/fr/plaintes",                                              "delai": "Legal",     "type": "autorite"},
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
        {"nom": "Google Alerts",    "desc": "Surveillance temps réel de votre nom",                          "url": "https://www.google.com/alerts",                "categorie": "surveillance"},
        {"nom": "Have I Been Pwned","desc": "Fuites de données par email",                                    "url": "https://haveibeenpwned.com",                   "categorie": "fuites"},
        {"nom": "JustDeleteMe",     "desc": "Liens directs pour supprimer vos comptes inscrits",             "url": "https://justdeleteme.xyz/fr",                  "categorie": "comptes"},
        {"nom": "Browserleaks",     "desc": "Ce que votre navigateur révèle aux sites",                      "url": "https://browserleaks.com/",                    "categorie": "technique"},
        {"nom": "Sherlock",         "desc": "OSINT username sur +300 sites",                                 "url": "https://github.com/sherlock-project/sherlock", "categorie": "technique"},
        {"nom": "Maltego CE",       "desc": "Cartographie OSINT graphique (version gratuite)",               "url": "https://www.maltego.com/maltego-community/",   "categorie": "technique"},
    ])


@app.route("/shutdown", methods=["POST"])
def shutdown():
    def stop():
        os._exit(0)
    threading.Timer(0.2, stop).start()
    return jsonify({"ok": True})