# DataEraser
**Outil local de nettoyage de présence numérique**

> Aucune donnée envoyée à des tiers. Tout tourne en local sur votre machine.

---
### IMPORTANT : SUIVRE LES ETAPES DE LA DOCUMENTATION CI DESSOUS

## Etapes d'installation 

> Télécharger le dossier ZIP (ou bien git clone pour les connaisseurs)
<img width="403" height="313" alt="zip" src="https://github.com/user-attachments/assets/eb189dd5-30a5-410b-91e0-e47aa69617f1" />

> Extraire le dossier : clic droit → "Extraire" ou "Extraire tout"
<img width="510" height="511" alt="extraire" src="https://github.com/user-attachments/assets/f5e704a6-c13c-49fb-8a54-31b44fb6ab3f" />

> Suivre les étapes ci dessous en fonction de votre système d'exploitation

## Lancement (choisissez selon votre système)

### Mac - double-cliquer sur `mac-start.command`
Si bloqué par macOS : clic droit → "Ouvrir" → "Ouvrir quand même"

### Windows - double-cliquer sur `windows-start`

### Linux - dans le terminal :
```bash
bash start.sh
```

> Le navigateur s'ouvre automatiquement sur http://localhost:5000
> Ctrl+C dans le terminal pour arrêter l'outil.

### Prérequis : Python 3.9+
- Mac : https://www.python.org/downloads/ (ou `brew install python`)
- Windows : https://www.python.org/downloads/ — cocher **"Add Python to PATH"**
- Linux : `sudo apt install python3 python3-pip`

Flask est installé automatiquement au premier lancement.

---

## Fonctionnalités

| Étape | Fonction | Mode |
|-------|----------|------|
| 01 Identité | Nom, prénom, variantes + choix des modes de recherche | Local |
| 02 Recherche | 14 moteurs × N variantes + 8 data brokers FR | Liens |
| 03 Fuites | Have I Been Pwned par email | Lien |
| 04 Emails RGPD | Génération Art.17 pour chaque site identifié | **100% local** |
| 05 Déréférencement | Formulaires Google, Bing, CNIL… + email générique | Liens |

---

## Modes de recherche
- **"Prénom Nom"** - avec guillemets (recherche exacte)
- **"Nom Prénom"** - avec guillemets (ordre inversé)
- **Prénom Nom** - sans guillemets (résultats plus larges)

Chaque moteur génère un lien par mode coché, déroulables en accordéon.

---

## RGPD — Base légale
- **Article 17** - Droit à l'effacement
- **Article 21** - Droit d'opposition
- Délai de réponse légal : **30 jours**
- Recours : **CNIL** (cnil.fr/fr/plaintes)
