<div id="top" align="center">

<!-- Shields Header -->
[![Contributors][contributors-shield]](https://github.com/franckferman/Scraping-Deputes-France/graphs/contributors)
[![Forks][forks-shield]](https://github.com/franckferman/Scraping-Deputes-France/network/members)
[![Stargazers][stars-shield]](https://github.com/franckferman/Scraping-Deputes-France/stargazers)
[![License][license-shield]](https://github.com/franckferman/Scraping-Deputes-France/blob/stable/LICENSE)

<!-- Logo -->
<a href="https://github.com/franckferman/Scraping-Deputes-France">
  <img src="https://raw.githubusercontent.com/franckferman/Scraping-Deputes-France/refs/heads/stable/docs/github/graphical_resources/Banner-Scraping-Deputes-France.png" alt="Scraping-Deputes-France Logo" width="auto" height="auto">
</a>

<!-- Title & Tagline -->
<h3 align="center">🏛️ Scraping-Deputes-France</h3>
<p align="center">
    <em>Scraping des député·e·s de l’Assemblée Nationale.</em>
    <br>
    Script pour scraper les député·e·s français (Nom, Région, Département, Email, Groupe, Circonscription) depuis le site de l'Assemblée nationale.
</p>

</div>

## 📜 Table of Contents

<details open>
  <summary><strong>Click to collapse/expand</strong></summary>
  <ol>
    <li><a href="#-about">📖 About</a></li>
    <li><a href="#-installation">🛠️ Installation</a></li>
    <li><a href="#-usage">🎮 Usage</a></li>
    <li><a href="#-contributing">🤝 Contributing</a></li>
    <li><a href="#%EF%B8%8F-legal-disclaimer">⚖️ Legal Disclaimer</a></li>
    <li><a href="#-star-evolution">🌠 Star Evolution</a></li>
    <li><a href="#-license">📜 License</a></li>
    <li><a href="#-contact">📞 Contact</a></li>
  </ol>
</details>

## 📖 About

**Scraping-Deputes-France:** _Un outil simple et efficace pour récupérer automatiquement les informations publiques des députés français : Noms, Régions, Départements, Emails, Groupes parlementaires et Circonscriptions — exportables en texte, JSON ou CSV._

L'idée de ce projet est née d'un besoin simple : pouvoir récupérer facilement les emails des députés d'une région donnée pour leur envoyer des mails groupés, notamment dans un cadre politique ou citoyen. Que ce soit pour interpeller les élus sur une cause, faire des demandes officielles, ou simplement avoir accès aux coordonnées publiques, cet outil automatise cette tâche.

J'ai notamment utilisé `Scraping-Deputes-France` dans le cadre du projet [LettreCitoyenne-Narcotrafic](https://github.com/franckferman/LettreCitoyenne-Narcotrafic), une initiative citoyenne visant à faciliter l'expression de l'opposition à la proposition de loi intitulée "Proposition de loi visant à sortir la France du piège du narcotrafic". Ce site permet aux citoyens de contacter directement leurs députés pour exprimer leurs préoccupations sur les implications de cette loi sur les libertés individuelles.

### ⚙️ Fonctionnalités principales de _Scraping-Deputes-France_

- 🔍 Scraping des députés : Récupération automatique des noms, départements, emails (adresse officielle privilégiée), groupes et circonscriptions — les 577 député·e·s.
- 📍 Sélection par région : 24 régions couvertes (`--region all`), outre-mer et Français de l'étranger inclus.
- 🚀 Multithreading : Accélération du scraping grâce à l'exécution parallèle (tri déterministe garanti).
- 🛡️ Robustesse : Session HTTP avec UA navigateur, retries sur erreurs transitoires (429/5xx, `Retry-After`, backoff exponentiel), alerte si la structure du site change.
- 📊 Affichage optimisé : Résultats sous forme de texte structuré ou tableau ASCII.
- 💾 Exportation : Formats texte, **JSON** et **CSV**, dans un fichier ou sur stdout (diagnostics sur stderr, codes de sortie exploitables en script).
- 🧪 Qualité : suite de tests offline + smoke test hebdomadaire en CI qui détecte un redesign du site.

<p align="center">
  <img src="https://raw.githubusercontent.com/franckferman/Scraping-Deputes-France/refs/heads/stable/docs/github/graphical_resources/Screenshot-Scraping-Deputes-France_Demo.png" alt="Scraping-Deputes-France Demo Screenshot" width="auto" height="auto">
</p>

<p align="right">(<a href="#top">🔼 Back to top</a>)</p>

## 🚀 Installation

Avant de commencer l'installation, assurez-vous de remplir les prérequis suivants.

### Prérequis

1. **Python 3**: Assurez-vous que Python 3 est installé sur votre système.

2. **Dépendances**: Installez les bibliothèques requises via pip en utilisant le fichier `requirements.txt`.

> ⚠️ **Note**: Scraping-Deputes-France a été testé avec Python 3.11.10 sous Linux. Bien qu'il puisse fonctionner avec d'autres versions, la compatibilité n'est garantie que pour cette configuration.

### Méthodes d'installation

1. **Cloner le dépôt via Git**:
```bash
git clone https://github.com/franckferman/Scraping-Deputes-France.git
```

2. **Installation sans Git (_téléchargement direct_)**:
Si vous ne souhaitez pas cloner tout le dépôt et avez juste besoin du script, vous pouvez le télécharger directement:
```bash
curl -O https://raw.githubusercontent.com/franckferman/Scraping-Deputes-France/stable/Scraping-Deputes-France.py
```

<p align="right">(<a href="#top">🔼 Back to top</a>)</p>

## 🎮 Usage

Assurez-vous d'adapter les commandes en fonction de la configuration de votre installation de `Scraping-Deputes-France`.

### **Démarrage rapide**

Pour afficher l'aide complète et explorer les fonctionnalités du script:

```bash
python3 Scraping-Deputes-France.py --help
```

### **Exemples de commandes**

#### 🔍 Scraper les informations des députés d'une région spécifique:

| Tâche | Commande |
| --- | --- |
| Scraper les députés des régions par défaut (Île-de-France & PACA) | `python3 Scraping-Deputes-France.py` |
| Scraper uniquement la région Bretagne | `python3 Scraping-Deputes-France.py --region Bretagne` |
| Scraper plusieurs régions spécifiques | `python3 Scraping-Deputes-France.py --region Bretagne Ile-de-France` |
| Scraper **toutes les régions** (24, dont outre-mer & Français de l'étranger) | `python3 Scraping-Deputes-France.py --region all` |
| Lister toutes les régions valides | `python3 Scraping-Deputes-France.py --list-regions` |
| Tester rapidement sur 10 députés | `python3 Scraping-Deputes-France.py --limit 10` |

#### 📄 Personnalisation des données récupérées:

| Tâche | Commande |
| --- | --- |
| Récupérer uniquement les noms et emails | `python3 Scraping-Deputes-France.py --fields nom,email` |
| Champs disponibles : `nom`, `region`, `departement`, `email`, `groupe`, `circonscription` | `python3 Scraping-Deputes-France.py --fields nom,departement` |
| Afficher les résultats sous forme de tableau ASCII | `python3 Scraping-Deputes-France.py --table` |
| Afficher les emails sans formatage ni séparateurs | `python3 Scraping-Deputes-France.py --fields email --barefields --no-separator` |

#### ⚡ Optimisation avec le multithreading:

| Tâche | Commande |
| --- | --- |
| Activer le multithreading avec 5 threads | `python3 Scraping-Deputes-France.py --threads 5` |
| Définir un délai de 2 secondes entre les tentatives en cas d'échec | `python3 Scraping-Deputes-France.py --retries 5 --delay 2 --timeout 15` |

#### 💾 Export des résultats:

| Tâche | Commande |
| --- | --- |
| Sauvegarder les résultats dans un fichier texte | `python3 Scraping-Deputes-France.py --output deputes.txt` |
| Exporter en **JSON** | `python3 Scraping-Deputes-France.py --format json --output deputes.json` |
| Exporter en **CSV** | `python3 Scraping-Deputes-France.py --format csv --output deputes.csv` |
| Sauvegarder uniquement les emails dans un fichier | `python3 Scraping-Deputes-France.py --fields email --barefields --output emails.txt` |

> **Codes de sortie :** `0` succès · `1` erreur de configuration (région/champ invalide, threads < 1) · `2` échec global (0 député récupéré). Les messages `[INFO]/[WARNING]/[ERROR]` passent par stderr — stdout reste propre pour être pipé (`json`, `csv`).

### 🧪 Tests

```bash
python3 -m pytest tests/ -q
```

Suite **offline** (15 tests) basée sur des fixtures HTML réelles du site : parsing régional, préservation des homonymes, préférence de l'email officiel, tableau ASCII, session/UA, codes de sortie de la CLI. En complément, un **smoke test hebdomadaire** en CI scrape réellement quelques fiches et échoue si la structure du site change.

<p align="right">(<a href="#top">🔼 Back to top</a>)</p>

## 🤝 Contributing

Vos contributions, retours et suggestions jouent un rôle essentiel dans l’amélioration continue de ce projet. Que ce soit pour signaler un problème, proposer une nouvelle fonctionnalité ou soumettre une amélioration, chaque contribution compte et est la bienvenue.

<p align="right">(<a href="#top">🔼 Back to top</a>)</p>

## ⚖️ Legal Disclaimer

L'outil `Scraping-Deputes-France` permet de récupérer des informations publiques disponibles sur le site de l'Assemblée nationale. Son utilisation doit impérativement respecter les lois et réglementations en vigueur dans votre pays ou région.

L'utilisation de cet outil est strictement interdite pour :

- Envoyer des emails de masse non sollicités (spam) aux députés.
- Harceler, menacer ou nuire à toute personne ou entité.
- Mener des actions illégales telles que la collecte abusive de données ou leur diffusion sans consentement légal.
- Automatiser du lobbying abusif ou fausser le débat démocratique par des actions coordonnées non transparentes.

Le créateur de `Scraping-Deputes-France` ne saurait être tenu responsable de toute utilisation abusive ou illégale de cet outil. En téléchargeant et en exécutant ce script, vous assumez l'entière responsabilité de votre usage et vous engagez à respecter les lois en vigueur.

⚠️ Si vous avez un doute sur la légalité de votre usage, consultez un juriste ou une autorité compétente avant d’utiliser cet outil.

🔹 En utilisant Scraping-Deputes-France, vous reconnaissez avoir lu, compris et accepté cette clause de non-responsabilité.

<p align="right">(<a href="#top">🔼 Back to top</a>)</p>

## 🌠 Star Evolution

Découvrez l’évolution des étoiles attribuées à ce projet et suivez sa croissance au fil du temps:

<a href="https://star-history.com/#franckferman/Scraping-Deputes-France&Timeline">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=franckferman/Scraping-Deputes-France&type=Timeline&theme=dark" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=franckferman/Scraping-Deputes-France&type=Timeline" />
  </picture>
</a>

Chaque étoile compte. Merci pour votre soutien. Vos encouragements nourrissent notre motivation et contribuent à l’évolution du projet. ✨

<p align="right">(<a href="#top">🔼 Back to top</a>)</p>

## 📚 License

Ce projet est sous licence GNU Affero General Public License, Version 3.0 (AGPL-3.0). Pour plus de détails, veuillez consulter le fichier de licence dans le dépôt: [Read the license on GitHub](https://github.com/franckferman/Scraping-Deputes-France/blob/stable/LICENSE)

<p align="right">(<a href="#top">🔼 Back to top</a>)</p>

## 📞 Contact

[![ProtonMail][protonmail-shield]](mailto:contact@franckferman.fr) 
[![LinkedIn][linkedin-shield]](https://www.linkedin.com/in/franckferman)
[![Twitter][twitter-shield]](https://www.twitter.com/franckferman)

<p align="right">(<a href="#top">🔼 Back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/franckferman/Scraping-Deputes-France.svg?style=for-the-badge
[contributors-url]: https://github.com/franckferman/Scraping-Deputes-France/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/franckferman/Scraping-Deputes-France.svg?style=for-the-badge
[forks-url]: https://github.com/franckferman/Scraping-Deputes-France/network/members
[stars-shield]: https://img.shields.io/github/stars/franckferman/Scraping-Deputes-France.svg?style=for-the-badge
[stars-url]: https://github.com/franckferman/Scraping-Deputes-France/stargazers
[license-shield]: https://img.shields.io/github/license/franckferman/Scraping-Deputes-France.svg?style=for-the-badge
[license-url]: https://github.com/franckferman/Scraping-Deputes-France/blob/stable/LICENSE
[protonmail-shield]: https://img.shields.io/badge/ProtonMail-8B89CC?style=for-the-badge&logo=protonmail&logoColor=blueviolet
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=blue
[twitter-shield]: https://img.shields.io/badge/-Twitter-black.svg?style=for-the-badge&logo=twitter&colorB=blue
