"""
Semantic verification - compare the real Article 8(2) text with the XML.

For each phrase of the provision we declare which predicate(s)/construct must
appear in the generated LegalRuleML. The script parses the XML, checks each one
is present, and prints a coverage table. Exit code 0 only if every phrase is
covered.

This answers the client's "validate against the provision" at the semantic
level (faithfulness), on top of the structural validator in validate.py.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import List

from lxml import etree

RULEML = "http://ruleml.org/spec"
LRML = "http://docs.oasis-open.org/legalruleml/ns/v1.0/"


@dataclass
class PhraseCheck:
    phrase: str          # span from the real text
    element: str         # what must appear in the XML
    kind: str            # "rel" | "modality" | "bearer" | "connective" | "paraphrase"
    needle: str          # value to look for


# The mapping: every phrase of Art 8(2) -> required XML element.
CHECKS: List[PhraseCheck] = [
    PhraseCheck("The controller", "Rel prOnto:Controller", "rel", "prOnto:Controller"),
    PhraseCheck("The controller (bearer)", "lrml:Bearer -> #controller", "bearer", "#controller"),
    PhraseCheck("shall", "lrml:Obligation", "modality", "Obligation"),
    PhraseCheck("make reasonable efforts", "Rel ex:ReasonableEffort", "rel", "ex:ReasonableEffort"),
    PhraseCheck("make ... efforts (by controller)", "Rel ex:makesEffort", "rel", "ex:makesEffort"),
    PhraseCheck("to verify", "Rel ex:hasPurposeToVerify", "rel", "ex:hasPurposeToVerify"),
    PhraseCheck("that consent", "Rel prOnto:Consent", "rel", "prOnto:Consent"),
    PhraseCheck("is given ... (disjunction)", "ruleml:Or", "connective", "Or"),
    PhraseCheck("is given", "Rel dapreco:givenBy", "rel", "dapreco:givenBy"),
    PhraseCheck("or authorised", "Rel dapreco:authorisedBy", "rel", "dapreco:authorisedBy"),
    PhraseCheck("by the holder of parental responsibility",
                "Rel ex:HolderOfParentalResponsibility", "rel",
                "ex:HolderOfParentalResponsibility"),
    PhraseCheck("over the child", "Rel prOnto:DataSubject / ex:Child", "rel", "ex:Child"),
    PhraseCheck("taking into consideration available technology",
                "Rel ex:takesIntoConsideration", "rel", "ex:takesIntoConsideration"),
    PhraseCheck("available technology", "Rel ex:AvailableTechnology", "rel",
                "ex:AvailableTechnology"),
    PhraseCheck("in such cases (-> Art 8(1)): offered to child",
                "Rel ex:offeredDirectlyToChild", "rel", "ex:offeredDirectlyToChild"),
    PhraseCheck("in such cases: consent-based processing (Art 6(1)(a))",
                "Rel ex:basedOnConsent", "rel", "ex:basedOnConsent"),
    PhraseCheck("in such cases: below consent age",
                "Rel ex:belowConsentAge", "rel", "ex:belowConsentAge"),
    PhraseCheck("provision text recorded", "lrml:Paraphrase", "paraphrase", ""),
]


def _collect(tree: etree._ElementTree):
    root = tree.getroot()
    rels = {el.get("iri") for el in root.iter(f"{{{RULEML}}}Rel")}
    ors = root.findall(f".//{{{RULEML}}}Or")
    modalities = {etree.QName(e).localname for e in root.iter()
                  if isinstance(e.tag, str)
                  and etree.QName(e).namespace == LRML
                  and etree.QName(e).localname in
                  {"Obligation", "Permission", "Prohibition", "Right"}}
    bearers = {b.get("keyref") for b in root.iter(f"{{{LRML}}}Bearer")}
    paraphrase = root.find(f".//{{{LRML}}}Paraphrase")
    return rels, ors, modalities, bearers, paraphrase


def compare(xml_path: str | pathlib.Path) -> bool:
    tree = etree.parse(str(xml_path))
    rels, ors, modalities, bearers, paraphrase = _collect(tree)

    rows = []
    all_ok = True
    for c in CHECKS:
        if c.kind == "rel":
            ok = c.needle in rels
        elif c.kind == "modality":
            ok = c.needle in modalities
        elif c.kind == "bearer":
            ok = c.needle in bearers
        elif c.kind == "connective":
            ok = len(ors) > 0
        elif c.kind == "paraphrase":
            ok = paraphrase is not None and bool((paraphrase.text or "").strip())
        else:
            ok = False
        all_ok = all_ok and ok
        rows.append((ok, c.phrase, c.element))

    # Render table
    wphrase = max(len(r[1]) for r in rows)
    welem = max(len(r[2]) for r in rows)
    print("Text <-> XML faithfulness check  (GDPR Art 8(2))")
    print("=" * (wphrase + welem + 12))
    print(f"{'':2} {'phrase in the law'.ljust(wphrase)}  {'XML element'.ljust(welem)}")
    print("-" * (wphrase + welem + 12))
    for ok, phrase, elem in rows:
        mark = "OK " if ok else "XX "
        print(f"{mark} {phrase.ljust(wphrase)}  {elem.ljust(welem)}")
    print("=" * (wphrase + welem + 12))
    covered = sum(1 for r in rows if r[0])
    print(f"Coverage: {covered}/{len(rows)} phrases represented")
    print("RESULT: " + ("FULLY FAITHFUL" if all_ok else "GAPS REMAIN"))
    return all_ok


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "output/gdpr_art8_2.lrml.xml"
    raise SystemExit(0 if compare(target) else 1)
