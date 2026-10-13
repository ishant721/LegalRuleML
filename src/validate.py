"""
Step 4 - Validate the LegalRuleML XML.

Two tiers:

  A. Always-on checks (no external files needed):
     1. XML well-formedness (lxml parse).
     2. Structural conformance to the LegalRuleML content model:
        - correct root element + required namespaces
        - a normative rule expressed as PrescriptiveStatement > ruleml:Rule
          with ruleml:if and ruleml:then
        - the conclusion carries a recognised deontic modality
        - referential integrity: every @keyref resolves to a defined @key
        - each Association's appliesSource/toTarget resolve

  B. Optional official-schema validation (RELAX NG / XSD):
     If a schema file path is provided (CLI/env), run lxml RelaxNG against it.
     Otherwise it is skipped with guidance (see schema/README.md).

Returns a ValidationReport; `ok` is True only if all tier-A checks pass.
"""
from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from lxml import etree

LRML = "http://docs.oasis-open.org/legalruleml/ns/v1.0/"
RULEML = "http://ruleml.org/spec"
DEONTIC = {"Obligation", "Permission", "Prohibition", "Right"}


@dataclass
class ValidationReport:
    checks: List[Tuple[str, bool, str]] = field(default_factory=list)
    schema_result: Optional[str] = None

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        self.checks.append((name, passed, detail))

    @property
    def ok(self) -> bool:
        return all(p for _, p, _ in self.checks)

    def render(self) -> str:
        lines = ["LegalRuleML validation report", "=" * 30]
        for name, passed, detail in self.checks:
            mark = "PASS" if passed else "FAIL"
            line = f"[{mark}] {name}"
            if detail:
                line += f"  -> {detail}"
            lines.append(line)
        if self.schema_result is not None:
            lines.append("-" * 30)
            lines.append(f"[schema] {self.schema_result}")
        lines.append("=" * 30)
        lines.append("RESULT: " + ("VALID" if self.ok else "INVALID"))
        return "\n".join(lines)


def _localname(el: etree._Element) -> str:
    return etree.QName(el).localname


def validate(xml_path: str | pathlib.Path,
             schema_path: Optional[str] = None) -> ValidationReport:
    xml_path = pathlib.Path(xml_path)
    report = ValidationReport()

    # --- A1. Well-formedness ------------------------------------------------
    try:
        tree = etree.parse(str(xml_path))
    except etree.XMLSyntaxError as exc:
        report.add("well-formed XML", False, str(exc))
        return report
    report.add("well-formed XML", True)
    root = tree.getroot()

    # --- A2. Root + namespaces ---------------------------------------------
    report.add(
        "root is lrml:LegalRuleML",
        etree.QName(root).namespace == LRML and _localname(root) == "LegalRuleML",
        f"got {root.tag}",
    )
    report.add("lrml namespace declared", LRML in root.nsmap.values())
    report.add("ruleml namespace declared", RULEML in root.nsmap.values())

    # --- A3. Legal source present ------------------------------------------
    sources = root.findall(f"{{{LRML}}}LegalSources/{{{LRML}}}LegalSource")
    report.add("has >=1 LegalSource", len(sources) >= 1, f"{len(sources)} found")

    # --- A4. Prescriptive rule with if/then --------------------------------
    rules = root.findall(
        f"{{{LRML}}}Statements/{{{LRML}}}PrescriptiveStatement/{{{RULEML}}}Rule"
    )
    report.add("has PrescriptiveStatement>Rule", len(rules) >= 1, f"{len(rules)} found")

    deontic_ok = False
    ifthen_ok = False
    for rule in rules:
        has_if = rule.find(f"{{{RULEML}}}if") is not None
        has_then = rule.find(f"{{{RULEML}}}then") is not None
        ifthen_ok = ifthen_ok or (has_if and has_then)
        then_el = rule.find(f"{{{RULEML}}}then")
        if then_el is not None:
            for child in then_el:
                if (etree.QName(child).namespace == LRML
                        and _localname(child) in DEONTIC):
                    deontic_ok = True
    report.add("Rule has if and then", ifthen_ok)
    report.add("conclusion carries a deontic modality "
               "(Obligation/Permission/Prohibition/Right)", deontic_ok)

    # --- A5. Referential integrity of key / keyref -------------------------
    keys = set()
    keyrefs = []
    for el in root.iter():
        if "key" in el.attrib:
            keys.add(el.attrib["key"])
        if "keyref" in el.attrib:
            keyrefs.append(el.attrib["keyref"].lstrip("#"))
    dangling = sorted({k for k in keyrefs if k not in keys})
    report.add("all keyref resolve to a key", not dangling,
               f"dangling: {dangling}" if dangling else f"{len(keyrefs)} refs ok")

    # --- A6. Associations resolve ------------------------------------------
    assoc_ok = True
    assoc_detail = "no Association elements"
    assocs = root.findall(f"{{{LRML}}}Associations/{{{LRML}}}Association")
    if assocs:
        assoc_detail = f"{len(assocs)} association(s)"
        for a in assocs:
            s = a.find(f"{{{LRML}}}appliesSource")
            t = a.find(f"{{{LRML}}}toTarget")
            for node in (s, t):
                if node is None or node.get("keyref", "").lstrip("#") not in keys:
                    assoc_ok = False
    report.add("Association appliesSource/toTarget resolve", assoc_ok, assoc_detail)

    # --- B. Optional official-schema validation ----------------------------
    schema_path = schema_path or os.environ.get("LRML_SCHEMA")
    if schema_path and pathlib.Path(schema_path).exists():
        try:
            sp = pathlib.Path(schema_path)
            if sp.suffix.lower() in {".rng"}:
                schema = etree.RelaxNG(etree.parse(str(sp)))
            elif sp.suffix.lower() in {".xsd"}:
                schema = etree.XMLSchema(etree.parse(str(sp)))
            else:
                raise ValueError("schema must be .rng or .xsd (compile .rnc->.rng with trang)")
            valid = schema.validate(tree)
            report.schema_result = (
                f"{sp.name}: {'VALID' if valid else 'INVALID'}"
                + ("" if valid else f" -> {schema.error_log}")
            )
        except Exception as exc:  # noqa: BLE001
            report.schema_result = f"schema check errored: {exc}"
    else:
        report.schema_result = (
            "official RELAX NG/XSD check skipped (no schema provided). "
            "See schema/README.md to run jing/xmllint against the OASIS schema."
        )

    return report


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "output/gdpr_art8_2.lrml.xml"
    rep = validate(target)
    print(rep.render())
    raise SystemExit(0 if rep.ok else 1)
