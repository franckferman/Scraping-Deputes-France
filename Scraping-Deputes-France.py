#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scraping-Deputes-France.py

Script pour scraper les député·e·s français (Nom, Région, Email, Groupe, Circonscription)
depuis le site de l'Assemblée nationale.

- Gestion des retries, délais, timeout, et multithreading
- Option d'affichage sous forme de tableau ASCII

Utilisation :
  python3 scrape_deputes_france.py --help  # Afficher l'aide complète
"""


import argparse
import concurrent.futures
import re
import time
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup


BASE_URL: str = "https://www.assemblee-nationale.fr"
DEPUTES_URL: str = "https://www2.assemblee-nationale.fr/deputes/liste/regions"


# Liste des régions (structurées en <h2> sur la page) valides sur le site de l'Assemblée nationale
VALID_REGIONS: List[str] = [
    "Auvergne-Rhône-Alpes",
    "Bourgogne-Franche-Comté",
    "Bretagne",
    "Centre-Val de Loire",
    "Corse",
    "Grand Est",
    "Hauts-de-France",
    "Ile-de-France",
    "Normandie",
    "Nouvelle-Aquitaine",
    "Occitanie",
    "Pays de la Loire",
    "Provence-Alpes-Côte d'Azur",
    "Réunion"
]


def normalize_region(region: str) -> Optional[str]:
    """
    Normalise un nom de région : supprime les espaces en trop et met en correspondance
    avec une région valide en ignorant la casse.

    Args:
        region (str): Nom de la région entrée par l'utilisateur.

    Returns:
        str | None: Nom normalisé de la région si valide, sinon None.
    """
    region = region.strip().lower()
    for valid_region in VALID_REGIONS:
        if region == valid_region.lower():
            return valid_region
    return None


def get_with_retries(
    url: str,
    max_retries: int,
    delay_between: float,
    timeout: float,
    debug: bool
) -> Optional[requests.Response]:
    """
    Effectue plusieurs tentatives d'une requête GET sur une URL donnée.

    Attends `delay_between` secondes entre chaque tentative si la précédente a échoué.
    Le timeout de la requête est fixé par `timeout`.

    Args:
        url (str): L'URL cible.
        max_retries (int): Nombre maximal de tentatives.
        delay_between (float): Délai entre les tentatives en secondes.
        timeout (float): Durée maximale d'attente pour la requête.
        debug (bool): Active le mode debug.

    Returns:
        Optional[requests.Response]: Réponse HTTP si succès, sinon None.
    """
    for attempt in range(1, max_retries + 1):
        try:
            if debug:
                print(f"[DEBUG] Attempt {attempt}/{max_retries} fetching: {url}")
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            print(f"[ERROR] Attempt {attempt} failed for {url}: {exc}")
            if attempt < max_retries and delay_between > 0:
                if debug:
                    print(f"[DEBUG] Sleeping {delay_between}s before retrying...")
                time.sleep(delay_between)
    return None


def get_deputes_from_region(
    region_name: str,
    max_retries: int,
    delay_between: float,
    timeout: float,
    debug: bool = False
) -> Dict[str, str]:
    """
    Récupère une liste de député·e·s pour une région donnée.

    Cette fonction extrait les noms et URLs des député·e·s d'une région spécifique
    sur la page `DEPUTES_URL`. L'HTML est structuré en sections `<h2>` pour les
    régions, `<h4 class='departementTitre'>` pour les départements, et des `<li>`
    contenant les liens vers les fiches des députés.

    Args:
        region_name (str): Nom de la région à scraper.
        max_retries (int): Nombre maximal de tentatives pour récupérer la page.
        delay_between (float): Temps d'attente entre chaque tentative (secondes).
        timeout (float): Temps limite d'attente pour la requête (secondes).
        debug (bool, optional): Active le mode debug. Par défaut `False`.

    Returns:
        Dict[str, str]: Dictionnaire `{Nom député: URL}` des député·e·s trouvés.
    """
    if debug:
        print(f"[DEBUG] Collecting deputies for region: {region_name}")

    resp = get_with_retries(
        DEPUTES_URL,
        max_retries=max_retries,
        delay_between=delay_between,
        timeout=timeout,
        debug=debug
    )
    if not resp:
        print(f"[ERROR] Could not fetch region page: {DEPUTES_URL}")
        return {}

    soup = BeautifulSoup(resp.text, "html.parser")
    region_h2 = None

    # Trouver la balise <h2> correspondant à la région recherchée (region_name)
    for h2_tag in soup.find_all("h2"):
        if h2_tag.get_text(strip=True) == region_name:
            region_h2 = h2_tag
            break

    if not region_h2:
        if debug:
            print(f"[WARNING] No <h2> found for region {region_name}.")
        return {}

    deputes_map: Dict[str, str] = {}

    # Parcourir les éléments suivants dans l'HTML
    for sibling in region_h2.next_siblings:
        if sibling.name == "h2":
            # Nouvelle région détectée -> arrêt
            break
        if sibling.name == "h4" and sibling.get("class") == ["departementTitre"]:
            # Récupérer les <li> suivants contenant les députés
            for sub_sib in sibling.next_siblings:
                if sub_sib.name in ("h4", "h2"):
                    # Nouvelle région ou département -> arrêt
                    break
                if sub_sib.name == "div":
                    li_tags = sub_sib.find_all("li")
                    for li_tag in li_tags:
                        a_tag = li_tag.find("a", href=True)
                        if a_tag and a_tag["href"].startswith("/deputes/fiche/"):
                            name = a_tag.get_text(strip=True)
                            full_url = BASE_URL + a_tag["href"]
                            deputes_map[name] = full_url

    if debug:
        print(f"[DEBUG] Deputies found for {region_name}: {list(deputes_map.keys())}")
    return deputes_map


def get_depute_info(
    name: str,
    url: str,
    region: str,
    max_retries: int,
    delay_between: float,
    timeout: float,
    debug: bool = False
) -> Dict[str, Optional[str]]:
    """
    Récupère les informations détaillées d'un député.

    Cette fonction extrait les informations suivantes depuis la page du député :
    - Nom
    - Région
    - Email (extrait du lien `mailto:`)
    - Groupe parlementaire
    - Circonscription

    Elle transforme l'URL `/deputes/fiche/OMC_PAxxxxxx` en `/dyn/deputes/PAxxxxxx`
    pour accéder à la version dynamique du profil.

    Args:
        name (str): Nom du député.
        url (str): URL du profil du député sur le site de l'Assemblée nationale.
        region (str): Région d'élection du député.
        max_retries (int): Nombre maximal de tentatives en cas d'échec.
        delay_between (float): Temps d'attente entre les tentatives (secondes).
        timeout (float): Délai maximal d'attente pour la requête (secondes).
        debug (bool, optional): Active le mode debug. Par défaut `False`.

    Returns:
        Dict[str, Optional[str]]: Dictionnaire contenant :
            - "nom" (str)
            - "region" (str)
            - "email" (str ou None)
            - "groupe" (str ou None)
            - "circonscription" (str ou None)
    """
    # Extraire l'ID du député (ex: OMC_PA12345)
    match_id = re.search(r"/deputes/fiche/OMC_PA(\d+)", url)
    if not match_id:
        if debug:
            print(f"[WARNING] Can't extract OMC_PA ID from {url}")
        return {
            "nom": name,
            "region": region,
            "email": None,
            "groupe": None,
            "circonscription": None,
        }

    deputy_id = f"PA{match_id.group(1)}"
    dyn_url = f"{BASE_URL}/dyn/deputes/{deputy_id}"

    # Récupération de la page dynamique du député
    resp = get_with_retries(
        dyn_url, max_retries, delay_between, timeout, debug
    )
    if not resp:
        if debug:
            print(f"[ERROR] Could not fetch {dyn_url} after retries.")
        return {
            "nom": name,
            "region": region,
            "email": None,
            "groupe": None,
            "circonscription": None,
        }

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extraction de l'email (mailto:)
    a_mail = soup.find("a", href=re.compile(r"^mailto:"))
    email = a_mail["href"].replace("mailto:", "") if a_mail else None
    if debug:
        print(f"[DEBUG] Email for {name} => {email}")

    # Extraction du groupe parlementaire
    group_tag = soup.find("a", class_="h4 _colored link")
    group = group_tag.get_text(strip=True) if group_tag else None

    # Extraction de la circonscription
    circ_div = soup.find("div", class_="_mb-small._centered-text")
    # Correction : s'il y a un point dans la classe -> on retente
    if not circ_div:
        circ_div = soup.find("div", class_="_mb-small _centered-text")
    circonscription = None
    if circ_div:
        big_span = circ_div.find("span", class_="_big")
        if big_span:
            circonscription = big_span.get_text(strip=True)

    return {
        "nom": name,
        "region": region,
        "email": email,
        "groupe": group,
        "circonscription": circonscription,
    }


def build_ascii_table(
    results: List[Dict[str, Optional[str]]],
    fields: List[str]
) -> str:
    """
    Construit un tableau ASCII récapitulatif des députés.

    Cette fonction génère un tableau ASCII à partir des données des députés.
    Elle ajuste dynamiquement la largeur des colonnes pour une meilleure lisibilité.

    Args:
        results (List[Dict[str, Optional[str]]]): 
            Liste des informations des députés (Nom, Région, Email...).
        fields (List[str]): 
            Liste des colonnes à afficher.

    Returns:
        str: Représentation ASCII du tableau.
    """
    if not results or not fields:
        return "[INFO] Aucune donnée disponible pour générer un tableau."

    # Création de l'en-tête
    header = [field.capitalize() for field in fields]
    rows = [header]

    # Ajoute les données
    for dep in results:
        row = [dep.get(f, "") or "" for f in fields]
        rows.append(row)

    # Largeur max. pour chaque colonne
    col_widths: List[int] = []
    for c in range(len(fields)):
        col_widths.append(
            max(len(str(rows[r][c])) for r in range(len(rows)))
        )

    # Construction du tableau
    lines: List[str] = []
    for i, row in enumerate(rows):
        cells = [str(cell).ljust(col_widths[c]) for c, cell in enumerate(row)]
        line = " | ".join(cells)
        lines.append(line)
        if i == 0:
            sep = "-+-".join("-" * w for w in col_widths)
            lines.append(sep)

    return "\n".join(lines)


def scrape_deputes(
    regions: List[str],
    multithreading: bool = False,
    max_threads: int = 5,
    output_file: Optional[str] = None,
    debug: bool = False,
    retries: int = 3,
    delay: float = 0.0,
    req_timeout: float = 10.0,
    fields: Optional[List[str]] = None,
    use_table: bool = False,
    barefields: bool = False,
    no_separator: bool = False,
) -> None:
    """
    Scrape les informations des député·e·s français (Nom, Région, Email, Groupe, Circonscription)
    pour les régions spécifiées.

    Args:
        regions (List[str]): Liste des régions à scraper.
        multithreading (bool): Active le mode multithreading pour accélérer le scraping.
        max_threads (int): Nombre maximum de threads utilisés si multithreading est activé.
        output_file (Optional[str]): Nom du fichier où enregistrer les résultats (si fourni).
        debug (bool): Active le mode debug pour afficher des logs détaillés.
        retries (int): Nombre maximum de tentatives en cas d'échec des requêtes.
        delay (float): Délai en secondes entre les tentatives en cas d'échec.
        req_timeout (float): Timeout (secondes) des requêtes HTTP.
        fields (Optional[List[str]]): Liste des champs à extraire (nom, email...).
        use_table (bool): Génère un tableau ASCII récapitulatif des députés.
        barefields (bool): Affiche uniquement les valeurs sans labels (utile pour export CSV-like).
        no_separator (bool): Supprime la ligne de séparation si --barefields + 1 champ.

    Returns:
        None: Affiche les résultats dans la console ou les enregistre dans un fichier.
    """
    if fields is None:
        fields = ["nom", "region", "email", "groupe", "circonscription"]

    # 1) Collecte des URLs des députés par région
    deputes_data: List[tuple] = []
    for region in regions:
        region_map = get_deputes_from_region(
            region,
            max_retries=retries,
            delay_between=delay,
            timeout=req_timeout,
            debug=debug
        )
        for dep_name, dep_url in region_map.items():
            deputes_data.append((dep_name, dep_url, region))

    if debug:
        print(f"[DEBUG] Found {len(deputes_data)} deputies total.")

    # 2) Récupération des informations détaillées
    results: List[Dict[str, Optional[str]]] = []
    if multithreading:
        if debug:
            print(f"[DEBUG] Using multithreading with {max_threads} workers.")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            future_map = {
                executor.submit(
                    get_depute_info,
                    dep_name,
                    dep_url,
                    dep_region,
                    retries,
                    delay,
                    req_timeout,
                    debug
                ): (dep_name, dep_url, dep_region)
                for (dep_name, dep_url, dep_region) in deputes_data
            }
            for future in concurrent.futures.as_completed(future_map):
                results.append(future.result())
    else:
        if debug:
            print("[DEBUG] Running sequentially.")
        for (dep_name, dep_url, dep_region) in deputes_data:
            info = get_depute_info(
                dep_name, dep_url, dep_region,
                retries, delay, req_timeout, debug
            )
            results.append(info)

    # 3) Mise en forme des résultats
    lines: List[str] = []
    # Condition : 1 seul champ, barefields, no_separator -> pas de lignes de tirets
    skip_separators: bool = (
        barefields and len(fields) == 1 and no_separator
    )

    for dep in results:
        for field in fields:
            val: str = dep.get(field, "") or ""
            if barefields:
                lines.append(val)
            else:
                lines.append(f"{field.capitalize()}: {val}")
        if not skip_separators:
            lines.append("-" * 40)

    # 4) Génération du tableau ASCII
    ascii_table: str = ""
    if use_table:
        ascii_table = "\n\n=== TABLEAU RÉCAPITULATIF ===\n"
        ascii_table += build_ascii_table(results, fields)
        ascii_table += "\n"

    final_output: str = "\n".join(lines) + ascii_table

    # 5) Enregistrement ou affichage
    if output_file:
        with open(output_file, "w", encoding="utf-8") as file_out:
            file_out.write(final_output)
        if debug:
            print(f"[DEBUG] Results saved to {output_file}")
    else:
        print(final_output)


def main() -> None:
    """
    Analyse les arguments passés en ligne de commande et lance le scraping
    des députés avec les options spécifiées.

    Args:
        --list-regions (bool) : Affiche la liste des régions valides et quitte.
        --region (str) : Liste des régions à scraper (ex: 'Île-de-France' 'Bretagne').
        --threads (int) : Nombre de threads à utiliser (1 = exécution séquentielle).
        --output (str) : Nom du fichier de sortie (si spécifié).
        --debug (bool) : Active le mode debug pour plus de logs.
        --retries (int) : Nombre de tentatives en cas d'échec des requêtes.
        --delay (float) : Délai en secondes entre les tentatives.
        --timeout (float) : Timeout (secondes) des requêtes HTTP.
        --fields (str) : Champs à récupérer, séparés par une virgule (ex: "nom,email").
        --table (bool) : Génère un tableau ASCII des résultats.
        --barefields (bool) : Affiche uniquement les valeurs sans labels.
        --no-separator (bool) : Supprime la ligne de séparation si --barefields + 1 champ.

    Returns:
        None: Exécute le script et affiche les résultats ou les enregistre.
    """
    parser = argparse.ArgumentParser(
        description="Scraping des informations des députés français (Nom, Région, Email, Groupe, Circonscription) depuis le site officiel de l'Assemblée nationale."
    )

    # Option pour lister les régions valides et quitter
    parser.add_argument("--list-regions", action="store_true",
                        help="Affiche la liste des régions valides et quitte.")

    # Régions à scraper
    parser.add_argument("--region", type=str, nargs="+",
                        help="Régions à scraper (ex: 'Ile-de-France' 'Bretagne'). Par défaut, Ile-de-France et Provence-Alpes-Côte d'Azur.")

    # Options de scraping
    parser.add_argument("--threads", type=int, default=1,
                        help="Nombre de threads à utiliser (1 = séquentiel).")
    parser.add_argument("--output", type=str,
                        help="Fichier où sauvegarder les résultats.")
    parser.add_argument("--debug", action="store_true",
                        help="Active le mode debug pour afficher plus de logs.")
    parser.add_argument("--retries", type=int, default=3,
                        help="Nombre de tentatives en cas d'échec des requêtes (3 par défaut).")
    parser.add_argument("--delay", type=float, default=0.0,
                        help="Délai en secondes entre tentatives en cas d'échec (0 par défaut).")
    parser.add_argument("--timeout", type=float, default=10.0,
                        help="Timeout (secondes) des requêtes HTTP (10s par défaut).")
    parser.add_argument("--fields", type=str,
                        help="Champs à récupérer, séparés par virgules (ex: 'nom,email').")
    parser.add_argument("--table", action="store_true",
                        help="Affiche un tableau ASCII des résultats.")
    parser.add_argument("--barefields", action="store_true",
                        help="Affiche uniquement les valeurs sans labels (ex: juste l'email).")
    parser.add_argument("--no-separator", action="store_true",
                        help="Si --barefields + 1 champ, supprime la ligne de séparation.")

    args = parser.parse_args()

    # Affichage de la liste des régions valides
    if args.list_regions:
        print(f"🌍 Régions valides :\n  - " + "\n  - ".join(VALID_REGIONS))
        exit(0)

    # Vérification du nombre de threads
    if args.threads < 1:
        print("[ERROR] Le nombre de threads doit être au moins 1.")
        exit(1)

    use_threads: bool = (args.threads > 1)

    # Vérification et normalisation des régions
    if args.region:
        selected_regions = [normalize_region(r) for r in args.region if normalize_region(r)]
        invalid_regions = [r for r in args.region if not normalize_region(r)]

        if invalid_regions:
            print(f"[ERROR] Régions invalides détectées: {', '.join(invalid_regions)}")
            print(f"[INFO] Liste des régions valides: {', '.join(VALID_REGIONS)}")
            exit(1)
    else:
        # Valeur par défaut si l'utilisateur ne spécifie rien
        selected_regions = ["Ile-de-France", "Provence-Alpes-Côte d'Azur"]

    # Parse des fields (si --fields est spécifié)
    if args.fields:
        selected_fields: List[str] = [f.strip() for f in args.fields.split(",")]
    else:
        selected_fields = None

    # Lancer le scraping
    scrape_deputes(
        regions=selected_regions,
        multithreading=use_threads,
        max_threads=args.threads,
        output_file=args.output,
        debug=args.debug,
        retries=args.retries,
        delay=args.delay,
        req_timeout=args.timeout,
        fields=selected_fields,
        use_table=args.table,
        barefields=args.barefields,
        no_separator=args.no_separator
    )


if __name__ == "__main__":
    main()
