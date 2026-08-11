#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scraping-Deputes-France.py

Script pour scraper les député·e·s français (Nom, Région, Département, Email, Groupe, Circonscription)
depuis le site de l'Assemblée nationale.

- Gestion des retries (429/5xx + Retry-After + backoff), session HTTP avec UA navigateur, multithreading
- Export txt / json / csv, affichage tableau ASCII
- 24 régions couvertes (--region all), y compris outre-mer et Français de l'étranger

Utilisation :
  python3 Scraping-Deputes-France.py --help
"""

import argparse
import concurrent.futures
import csv
import io
import json
import re
import sys
import threading
import time
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup


BASE_URL: str = "https://www.assemblee-nationale.fr"
DEPUTES_URL: str = "https://www2.assemblee-nationale.fr/deputes/liste/regions"

# Un UA navigateur : le UA par défaut ("python-requests/x.y") est typiquement
# bloqué par les sites institutionnels.
USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Une Session par thread (connexions réutilisées; requests.Session n'est pas
# thread-safe, d'où le thread-local).
_tls = threading.local()


def get_session() -> requests.Session:
    """Retourne la Session HTTP du thread courant (créée à la demande)."""
    if getattr(_tls, "session", None) is None:
        _tls.session = requests.Session()
        _tls.session.headers.update({"User-Agent": USER_AGENT})
    return _tls.session

# Liste des régions (structurées en <h2> sur la page) valides sur le site de l'Assemblée nationale.
# Vérifiée en live (août 2026) : 24 sections, y compris l'outre-mer et les Français de l'étranger.
VALID_REGIONS: List[str] = [
    "Auvergne-Rhône-Alpes",
    "Bourgogne-Franche-Comté",
    "Bretagne",
    "Centre-Val de Loire",
    "Corse",
    "Français établis hors de France",
    "Grand Est",
    "Guadeloupe",
    "Guyane",
    "Hauts-de-France",
    "Ile-de-France",
    "Martinique",
    "Mayotte",
    "Normandie",
    "Nouvelle-Aquitaine",
    "Nouvelle-Calédonie",
    "Occitanie",
    "Pays de la Loire",
    "Polynésie française",
    "Provence-Alpes-Côte d'Azur",
    "Réunion",
    "Saint-Barthélemy et Saint-Martin",
    "Saint-Pierre-et-Miquelon",
    "Wallis-et-Futuna",
]


# Champs extractibles (validés dans --fields)
KNOWN_FIELDS: List[str] = ["nom", "region", "departement", "email", "groupe", "circonscription"]


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

    Ne reteste que les erreurs transitoires (429, 5xx, erreurs réseau) : un 4xx
    est définitif et retourné tel quel immédiatement. Respecte l'en-tête
    `Retry-After` si présent, sinon backoff exponentiel (ou `delay_between`
    si explicitement fourni). Utilise la Session du thread (UA navigateur,
    connexions réutilisées).

    Args:
        url (str): L'URL cible.
        max_retries (int): Nombre maximal de tentatives.
        delay_between (float): Délai entre les tentatives en secondes
            (0 = backoff exponentiel automatique).
        timeout (float): Durée maximale d'attente pour la requête.
        debug (bool): Active le mode debug.

    Returns:
        Optional[requests.Response]: Réponse HTTP si succès, sinon None.
    """
    session = get_session()
    for attempt in range(1, max_retries + 1):
        try:
            if debug:
                print(f"[DEBUG] Attempt {attempt}/{max_retries} fetching: {url}", file=sys.stderr)
            resp = session.get(url, timeout=timeout)
            # 4xx (hors 429) : erreur définitive, inutile de retester
            if 400 <= resp.status_code < 500 and resp.status_code != 429:
                print(f"[ERROR] {url} returned HTTP {resp.status_code} (not retried, file=sys.stderr)")
                return None
            if resp.status_code == 429 or resp.status_code >= 500:
                raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            resp.raise_for_status()
            return resp
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            print(f"[ERROR] Attempt {attempt} failed for {url}: {exc}", file=sys.stderr)
            if attempt < max_retries:
                # Retry-After prioritaire, sinon délai explicite, sinon backoff exponentiel
                retry_after = getattr(getattr(exc, "response", None), "headers", {}).get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait = float(retry_after)
                elif delay_between > 0:
                    wait = delay_between
                else:
                    wait = min(2 ** (attempt - 1), 30)
                if debug:
                    print(f"[DEBUG] Sleeping {wait}s before retrying...", file=sys.stderr)
                time.sleep(wait)
    return None


def parse_deputes_from_region(
    soup: BeautifulSoup,
    region_name: str,
    debug: bool = False
) -> List[tuple]:
    """
    Extrait les député·e·s d'une région depuis une page liste déjà parsée.

    L'HTML est structuré en sections `<h2>` pour les régions,
    `<h4 class='departementTitre'>` pour les départements, et des `<li>`
    contenant les liens vers les fiches des députés.

    Args:
        soup (BeautifulSoup): Page liste des députés déjà téléchargée et parsée.
        region_name (str): Nom de la région à extraire.
        debug (bool, optional): Active le mode debug. Par défaut `False`.

    Returns:
        List[tuple]: Liste de tuples `(nom, url, departement)` — une liste et
            non un dict, pour ne pas écraser silencieusement les homonymes.
    """
    region_h2 = None

    # Trouver la balise <h2> correspondant à la région recherchée (region_name)
    for h2_tag in soup.find_all("h2"):
        if h2_tag.get_text(strip=True) == region_name:
            region_h2 = h2_tag
            break

    if not region_h2:
        print(f"[WARNING] No <h2> found for region {region_name} — "
              f"la structure du site a-t-elle changé ?", file=sys.stderr)
        return []

    deputes_list: List[tuple] = []
    current_departement: Optional[str] = None

    # Parcourir les éléments suivants dans l'HTML
    for sibling in region_h2.next_siblings:
        if sibling.name == "h2":
            # Nouvelle région détectée -> arrêt
            break
        if sibling.name == "h4" and sibling.get("class") == ["departementTitre"]:
            current_departement = sibling.get_text(strip=True) or None
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
                            deputes_list.append((name, full_url, current_departement))

    if debug:
        print(f"[DEBUG] Deputies found for {region_name}: {[d[0] for d in deputes_list]}", file=sys.stderr)
    if not deputes_list:
        print(f"[WARNING] 0 député trouvé pour {region_name} — "
              f"la structure du site a-t-elle changé ?", file=sys.stderr)
    return deputes_list


def get_deputes_from_region(
    region_name: str,
    max_retries: int,
    delay_between: float,
    timeout: float,
    debug: bool = False
) -> Dict[str, str]:
    """
    Récupère une liste de député·e·s pour une région donnée (compatibilité).

    Télécharge la page liste puis la parse pour la région demandée.
    Préférez `parse_deputes_from_region` quand plusieurs régions sont
    traitées, pour ne télécharger la page qu'une seule fois.

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
        print(f"[DEBUG] Collecting deputies for region: {region_name}", file=sys.stderr)

    resp = get_with_retries(
        DEPUTES_URL,
        max_retries=max_retries,
        delay_between=delay_between,
        timeout=timeout,
        debug=debug
    )
    if not resp:
        print(f"[ERROR] Could not fetch region page: {DEPUTES_URL}", file=sys.stderr)
        return {}

    deputes_list = parse_deputes_from_region(
        BeautifulSoup(resp.text, "html.parser"), region_name, debug
    )
    return {name: url for name, url, _dept in deputes_list}


def get_depute_info(
    name: str,
    url: str,
    region: str,
    departement: Optional[str],
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
    - Département (issu de la page liste)
    - Email (extrait du lien `mailto:`)
    - Groupe parlementaire
    - Circonscription

    Elle transforme l'URL `/deputes/fiche/OMC_PAxxxxxx` en `/dyn/deputes/PAxxxxxx`
    pour accéder à la version dynamique du profil.

    Args:
        name (str): Nom du député.
        url (str): URL du profil du député sur le site de l'Assemblée nationale.
        region (str): Région d'élection du député.
        departement (str | None): Département d'élection (page liste).
        max_retries (int): Nombre maximal de tentatives en cas d'échec.
        delay_between (float): Temps d'attente entre les tentatives (secondes).
        timeout (float): Délai maximal d'attente pour la requête (secondes).
        debug (bool, optional): Active le mode debug. Par défaut `False`.

    Returns:
        Dict[str, Optional[str]]: Dictionnaire contenant :
            - "nom" (str)
            - "region" (str)
            - "departement" (str ou None)
            - "email" (str ou None)
            - "groupe" (str ou None)
            - "circonscription" (str ou None)
    """
    # Extraire l'ID du député (ex: OMC_PA12345)
    match_id = re.search(r"/deputes/fiche/OMC_PA(\d+)", url)
    if not match_id:
        if debug:
            print(f"[WARNING] Can't extract OMC_PA ID from {url}", file=sys.stderr)
        return {
            "nom": name,
            "region": region,
            "departement": departement,
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
            print(f"[ERROR] Could not fetch {dyn_url} after retries.", file=sys.stderr)
        return {
            "nom": name,
            "region": region,
            "departement": departement,
            "email": None,
            "groupe": None,
            "circonscription": None,
        }

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extraction de l'email : la fiche peut contenir PLUSIEURS mailto (adresse
    # officielle @assemblee-nationale.fr, contact perso, webmestre...). On
    # préfère l'adresse officielle, sinon premier mailto, sinon None.
    mailtos = [a["href"].replace("mailto:", "").split("?")[0]
               for a in soup.find_all("a", href=re.compile(r"^mailto:"))]
    email = next((m for m in mailtos if m.lower().endswith("@assemblee-nationale.fr")),
                 mailtos[0] if mailtos else None)
    if debug:
        print(f"[DEBUG] Email for {name} => {email} (candidates: {mailtos}, file=sys.stderr)")

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
        "departement": departement,
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
    output_format: str = "txt",
    limit: Optional[int] = None,
) -> int:
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
        fields = ["nom", "region", "departement", "email", "groupe", "circonscription"]

    # 1) Collecte des URLs des députés par région — UNE SEULE requête pour
    # toutes les régions (avant : la page liste était re-téléchargée par région)
    resp = get_with_retries(
        DEPUTES_URL,
        max_retries=retries,
        delay_between=delay,
        timeout=req_timeout,
        debug=debug
    )
    if not resp:
        print(f"[ERROR] Could not fetch deputies list page: {DEPUTES_URL}", file=sys.stderr)
        return 0

    list_soup = BeautifulSoup(resp.text, "html.parser")
    deputes_data: List[tuple] = []
    for region in regions:
        region_list = parse_deputes_from_region(list_soup, region, debug)
        for dep_name, dep_url, dep_departement in region_list:
            deputes_data.append((dep_name, dep_url, region, dep_departement))

    if debug:
        print(f"[DEBUG] Found {len(deputes_data, file=sys.stderr)} deputies total.")

    # --limit : plafond global (utile pour tester rapidement)
    if limit is not None and limit >= 0:
        deputes_data = deputes_data[:limit]
        if debug:
            print(f"[DEBUG] Limited to {len(deputes_data, file=sys.stderr)} deputies (--limit).")

    started_at = time.time()

    # 2) Récupération des informations détaillées
    results: List[Dict[str, Optional[str]]] = []
    if multithreading:
        if debug:
            print(f"[DEBUG] Using multithreading with {max_threads} workers.", file=sys.stderr)
        done_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            future_map = {
                executor.submit(
                    get_depute_info,
                    dep_name,
                    dep_url,
                    dep_region,
                    dep_departement,
                    retries,
                    delay,
                    req_timeout,
                    debug
                ): (dep_name, dep_url, dep_region, dep_departement)
                for (dep_name, dep_url, dep_region, dep_departement) in deputes_data
            }
            for future in concurrent.futures.as_completed(future_map):
                results.append(future.result())
                done_count += 1
                if done_count % 25 == 0 or done_count == len(deputes_data):
                    print(f"[INFO] Progression: {done_count}/{len(deputes_data)}", file=sys.stderr)
    else:
        if debug:
            print("[DEBUG] Running sequentially.", file=sys.stderr)
        for idx, (dep_name, dep_url, dep_region, dep_departement) in enumerate(deputes_data, 1):
            info = get_depute_info(
                dep_name, dep_url, dep_region, dep_departement,
                retries, delay, req_timeout, debug
            )
            results.append(info)
            if idx % 25 == 0 or idx == len(deputes_data):
                print(f"[INFO] Progression: {idx}/{len(deputes_data)}", file=sys.stderr)

    # Tri déterministe (région puis nom) — indispensable en mode threads,
    # où l'ordre d'arrivée est non déterministe
    results.sort(key=lambda d: ((d.get("region") or ""), (d.get("nom") or "")))

    incomplete = sum(1 for d in results if not d.get("email") and not d.get("groupe"))
    print(f"[INFO] {len(results)} député(s) scrapé(s) en {time.time() - started_at:.1f}s"
          + (f" — {incomplete} fiche(s) incomplète(s)" if incomplete else ""),
          file=sys.stderr)

    # 3) Mise en forme des résultats
    if output_format == "json":
        final_output: str = json.dumps(results, ensure_ascii=False, indent=2) + "\n"
    elif output_format == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for dep in results:
            writer.writerow({f: dep.get(f) or "" for f in fields})
        final_output = buf.getvalue()
    else:
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

        final_output = "\n".join(lines) + ascii_table

    # 5) Enregistrement ou affichage
    if output_file:
        with open(output_file, "w", encoding="utf-8") as file_out:
            file_out.write(final_output)
        if debug:
            print(f"[DEBUG] Results saved to {output_file}", file=sys.stderr)
    else:
        print(final_output)

    return len(results)


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
                        help="Régions à scraper (ex: 'Ile-de-France' 'Bretagne'), ou 'all' pour toutes. Par défaut, Ile-de-France et Provence-Alpes-Côte d'Azur.")

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
    parser.add_argument("--format", choices=["txt", "json", "csv"], default="txt",
                        help="Format de sortie : txt (défaut), json ou csv. --table/--barefields ne s'appliquent qu'au format txt.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Nombre maximal de députés à scraper (toutes régions confondues) — utile pour tester.")
    parser.add_argument("--barefields", action="store_true",
                        help="Affiche uniquement les valeurs sans labels (ex: juste l'email).")
    parser.add_argument("--no-separator", action="store_true",
                        help="Si --barefields + 1 champ, supprime la ligne de séparation.")

    args = parser.parse_args()

    # Affichage de la liste des régions valides
    if args.list_regions:
        print(f"🌍 Régions valides :\n  - " + "\n  - ".join(VALID_REGIONS))
        sys.exit(0)

    # Vérification du nombre de threads
    if args.threads < 1:
        print("[ERROR] Le nombre de threads doit être au moins 1.", file=sys.stderr)
        sys.exit(1)

    use_threads: bool = (args.threads > 1)

    # Vérification et normalisation des régions
    if args.region:
        if any(r.strip().lower() == "all" for r in args.region):
            selected_regions = list(VALID_REGIONS)
            invalid_regions = []
        else:
            selected_regions = [normalize_region(r) for r in args.region if normalize_region(r)]
            invalid_regions = [r for r in args.region if not normalize_region(r)]

        if invalid_regions:
            print(f"[ERROR] Régions invalides détectées: {', '.join(invalid_regions)}", file=sys.stderr)
            print(f"[INFO] Liste des régions valides: {', '.join(VALID_REGIONS)} (ou 'all')", file=sys.stderr)
            sys.exit(1)
    else:
        # Valeur par défaut si l'utilisateur ne spécifie rien
        selected_regions = ["Ile-de-France", "Provence-Alpes-Côte d'Azur"]

    # Parse des fields (si --fields est spécifié)
    if args.fields:
        selected_fields: List[str] = [f.strip().lower() for f in args.fields.split(",")]
        unknown_fields = [f for f in selected_fields if f not in KNOWN_FIELDS]
        if unknown_fields:
            print(f"[ERROR] Champs inconnus: {', '.join(unknown_fields)}", file=sys.stderr)
            print(f"[INFO] Champs valides: {', '.join(KNOWN_FIELDS)}", file=sys.stderr)
            sys.exit(1)
    else:
        selected_fields = None

    # Lancer le scraping
    scraped = scrape_deputes(
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
        no_separator=args.no_separator,
        output_format=args.format,
        limit=args.limit,
    )
    # 0 si au moins un député récupéré, 2 sinon (échec global)
    sys.exit(0 if scraped > 0 else 2)


if __name__ == "__main__":
    main()
