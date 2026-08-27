<div id="top" align="center">

<a href="https://github.com/franckferman/Scraping-Deputes-France">
  <img src="https://raw.githubusercontent.com/franckferman/Scraping-Deputes-France/refs/heads/stable/docs/github/graphical_resources/Banner-Scraping-Deputes-France.png" alt="Scraping-Deputes-France" width="auto" height="auto">
</a>

<h3 align="center">Scraping-Deputes-France</h3>
<p align="center">
    Extraction des informations publiques des députés de l'Assemblée nationale (nom, région, département, groupe, circonscription, contact) vers texte, JSON ou CSV.
</p>

</div>

## Table of Contents

<details open>
  <summary><strong>Click to collapse/expand</strong></summary>
  <ol>
    <li><a href="#about">About</a></li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#legal-disclaimer">Legal Disclaimer</a></li>
  </ol>
</details>

## About

**Scraping-Deputes-France** récupère les informations publiques des 577 députés français (nom, région, département, groupe parlementaire, circonscription et adresse de contact institutionnelle) depuis le site de l'Assemblée nationale, et les exporte en texte, JSON ou CSV.

L'idée de ce projet est née d'un besoin simple : pouvoir récupérer facilement les emails des députés d'une région donnée pour leur envoyer des mails groupés, notamment dans un cadre politique ou citoyen. Que ce soit pour interpeller les élus sur une cause, faire des demandes officielles, ou simplement avoir accès aux coordonnées publiques, cet outil automatise cette tâche.

Scraping-Deputes-France a notamment été utilisé dans le cadre du projet [LettreCitoyenne-Narcotrafic](https://github.com/franckferman/LettreCitoyenne-Narcotrafic), une initiative citoyenne visant à faciliter l'expression de l'opposition à la « Proposition de loi visant à sortir la France du piège du narcotrafic ». Ce site permet aux citoyens de contacter directement leurs députés pour exprimer leurs préoccupations sur les implications de cette loi sur les libertés individuelles.

### Fonctionnalités

- Couverture complète : les 577 députés, 24 régions incluant l'outre-mer et les Français de l'étranger (`--region all`).
- Champs extraits : nom, région, département, email (adresse institutionnelle privilégiée), groupe, circonscription.
- Sorties : texte, JSON ou CSV, dans un fichier ou sur la sortie standard.
- Multithreading optionnel, avec un ordre de sortie déterministe.
- Robustesse : session HTTP avec User-Agent navigateur, réessais sur erreurs transitoires (429/5xx, `Retry-After`, backoff exponentiel), alerte si la structure du site change.

<p align="right">(<a href="#top">Back to top</a>)</p>

## Usage

Aide complète :

```bash
python3 Scraping-Deputes-France.py --help
```

### Régions

| Tâche | Commande |
| --- | --- |
| Régions par défaut (Île-de-France et PACA) | `python3 Scraping-Deputes-France.py` |
| Une région | `python3 Scraping-Deputes-France.py --region Bretagne` |
| Plusieurs régions | `python3 Scraping-Deputes-France.py --region Bretagne Ile-de-France` |
| Toutes les régions (24) | `python3 Scraping-Deputes-France.py --region all` |
| Lister les régions valides | `python3 Scraping-Deputes-France.py --list-regions` |
| Limiter le nombre de fiches | `python3 Scraping-Deputes-France.py --limit 10` |

### Champs

Champs disponibles : `nom`, `region`, `departement`, `email`, `groupe`, `circonscription`.

| Tâche | Commande |
| --- | --- |
| Sélectionner des champs | `python3 Scraping-Deputes-France.py --fields nom,email` |
| Tableau ASCII | `python3 Scraping-Deputes-France.py --table` |
| Valeurs brutes, sans libellés | `python3 Scraping-Deputes-France.py --fields email --barefields --no-separator` |

### Performance

| Tâche | Commande |
| --- | --- |
| Multithreading (5 threads) | `python3 Scraping-Deputes-France.py --threads 5` |
| Réessais et délais réseau | `python3 Scraping-Deputes-France.py --retries 5 --delay 2 --timeout 15` |

### Export

| Tâche | Commande |
| --- | --- |
| Fichier texte | `python3 Scraping-Deputes-France.py --output deputes.txt` |
| JSON | `python3 Scraping-Deputes-France.py --format json --output deputes.json` |
| CSV | `python3 Scraping-Deputes-France.py --format csv --output deputes.csv` |
| Emails seuls dans un fichier | `python3 Scraping-Deputes-France.py --fields email --barefields --output emails.txt` |

Codes de sortie : `0` succès, `1` erreur de configuration (région ou champ invalide, `--threads` < 1), `2` aucun député récupéré. Les messages de diagnostic sont émis sur `stderr` ; `stdout` ne contient que les résultats, pour un usage en pipe (`json`, `csv`).

<p align="right">(<a href="#top">Back to top</a>)</p>

## Installation

Python 3.11 ou supérieur.

```bash
git clone https://github.com/franckferman/Scraping-Deputes-France.git
cd Scraping-Deputes-France
pip install -r requirements.txt
```

Pour n'utiliser que le script, sans cloner le dépôt :

```bash
curl -O https://raw.githubusercontent.com/franckferman/Scraping-Deputes-France/stable/Scraping-Deputes-France.py
pip install requests beautifulsoup4
```

<p align="right">(<a href="#top">Back to top</a>)</p>

## Legal Disclaimer

L'outil `Scraping-Deputes-France` permet de récupérer des informations publiques disponibles sur le site de l'Assemblée nationale. Son utilisation doit impérativement respecter les lois et réglementations en vigueur dans votre pays ou région.

L'utilisation de cet outil est strictement interdite pour :

- Envoyer des emails de masse non sollicités (spam) aux députés.
- Harceler, menacer ou nuire à toute personne ou entité.
- Mener des actions illégales telles que la collecte abusive de données ou leur diffusion sans consentement légal.
- Automatiser du lobbying abusif ou fausser le débat démocratique par des actions coordonnées non transparentes.

Le créateur de `Scraping-Deputes-France` ne saurait être tenu responsable de toute utilisation abusive ou illégale de cet outil. En téléchargeant et en exécutant ce script, vous assumez l'entière responsabilité de votre usage et vous engagez à respecter les lois en vigueur.

En cas de doute sur la légalité de votre usage, consultez un juriste ou une autorité compétente avant d'utiliser cet outil. En utilisant Scraping-Deputes-France, vous reconnaissez avoir lu, compris et accepté cette clause de non-responsabilité.

<p align="right">(<a href="#top">Back to top</a>)</p>
