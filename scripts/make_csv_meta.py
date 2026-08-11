#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dérive docs/data/deputes.csv + docs/data/meta.json depuis deputes.json.

Utilisé en local et par le workflow data.yml après le scrape JSON, pour
garantir un CSV et des métadonnées cohérents (une seule source de vérité :
le JSON produit par le scraper). Échoue si le jeu de données est
anormalement petit (garde-fou anti-redesign du site).
"""
import csv
import datetime
import json
import pathlib
import sys

DATA = pathlib.Path("docs/data")
FIELDS = ["nom", "region", "departement", "email", "groupe", "circonscription"]
MIN_EXPECTED = 400  # ~577 attendus ; en dessous, la structure du site a probablement changé


def main() -> None:
    src = DATA / "deputes.json"
    rows = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or len(rows) < MIN_EXPECTED:
        sys.exit(f"[ERREUR] Seulement {len(rows)} député(s) dans {src} — "
                 f"structure du site changée ? (attendu >= {MIN_EXPECTED})")

    with open(DATA / "deputes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: (r.get(k) or "") for k in FIELDS})

    meta = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "count": len(rows),
        "source": "https://www.assemblee-nationale.fr/",
    }
    (DATA / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"OK: {len(rows)} député(s) -> deputes.csv + meta.json")


if __name__ == "__main__":
    main()
