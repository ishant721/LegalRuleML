"""
GDPR Article 8(2) -> OASIS LegalRuleML : end-to-end pipeline.

    fetch (gdpr-info.eu)  ->  identify entities  ->  build LegalRuleML  ->  validate

Run:
    python main.py                # live fetch, falls back to cache if offline
    python main.py --offline      # force the bundled cached provision text
    python main.py --no-validate  # skip validation
    python main.py --schema path/to/legalruleml.rng   # also run official schema

Outputs (in ./output):
    article_8.json             the fetched/parsed provision
    gdpr_art8_2.lrml.xml       the LegalRuleML document
    validation_report.txt      the validation result
"""
from __future__ import annotations

import argparse
import json
import pathlib

from src.fetch_article import fetch_article_8
from src.entities import summary as entity_summary
from src.build_legalruleml import write as write_lrml
from src.validate import validate
from src.compare import compare

OUT = pathlib.Path(__file__).resolve().parent / "output"


def _hr(title: str) -> None:
    print("\n" + "=" * 68)
    print(title)
    print("=" * 68)


def main() -> int:
    ap = argparse.ArgumentParser(description="GDPR Art 8(2) -> LegalRuleML")
    ap.add_argument("--offline", action="store_true", help="use bundled cached text")
    ap.add_argument("--no-validate", action="store_true", help="skip validation")
    ap.add_argument("--schema", default=None, help="path to official .rng/.xsd schema")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    # --- Step 1: fetch ------------------------------------------------------
    _hr("STEP 1  Fetch GDPR Article 8 (source: gdpr-info.eu)")
    article = fetch_article_8(force_offline=args.offline)
    (OUT / "article_8.json").write_text(
        json.dumps(article, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"source     : {article['source_url']}")
    print(f"retrieved  : {article['retrieved_at']}")
    print(f"Art 8(2)   : {article['paragraphs']['2']}")
    print(f"saved      : output/article_8.json")

    # --- Step 2: identify normative elements --------------------------------
    _hr("STEP 2  Identify actor / action / conditions / modality")
    print(entity_summary())

    # --- Step 3: build LegalRuleML -----------------------------------------
    _hr("STEP 3  Build OASIS LegalRuleML XML")
    xml_path = write_lrml(OUT / "gdpr_art8_2.lrml.xml")
    print(f"saved      : output/{xml_path.name}")
    print("\n--- gdpr_art8_2.lrml.xml ---")
    print(xml_path.read_text(encoding="utf-8"))

    # --- Step 4: validate ---------------------------------------------------
    if args.no_validate:
        print("\n(validation skipped)")
        return 0
    _hr("STEP 4  Validate structure against the LegalRuleML standard")
    report = validate(xml_path, schema_path=args.schema)
    print(report.render())
    (OUT / "validation_report.txt").write_text(report.render(), encoding="utf-8")
    print("\nsaved      : output/validation_report.txt")

    # --- Step 5: compare real text vs XML (semantic faithfulness) -----------
    _hr("STEP 5  Compare the real provision text with the XML")
    faithful = compare(xml_path)

    return 0 if (report.ok and faithful) else 1


if __name__ == "__main__":
    raise SystemExit(main())
