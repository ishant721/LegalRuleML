"""
Step 3 - Build the OASIS LegalRuleML XML from the normative model.

Produces a LegalRuleML Core v1.0 document for GDPR Article 8(2):

  lrml:LegalRuleML
   |- lrml:LegalSources               provenance: which provision this encodes
   |- lrml:Statements
   |   `- lrml:PrescriptiveStatement      (a norm, not a fact/definition)
   |        |- lrml:Paraphrase            verbatim text of the provision
   |        `- ruleml:Rule                universally-quantified implication
   |             |- ruleml:if  -> ruleml:And( condition atoms )          [Art 8(1)]
   |             `- ruleml:then -> lrml:Obligation
   |                                 |- lrml:Bearer  -> the controller
   |                                 `- ruleml:And( ... ruleml:Or(...) ) the duty
   `- lrml:Associations               binds the rule back to its LegalSource

Every phrase of Art 8(2) is rendered as an explicit atom; the
"given or authorised" disjunction uses ruleml:Or.
"""
from __future__ import annotations

import pathlib
from lxml import etree

from .entities import MODEL, Atom, And, Or, Var, Ind, Formula

# --- Namespaces --------------------------------------------------------------
LRML = "http://docs.oasis-open.org/legalruleml/ns/v1.0/"
RULEML = "http://ruleml.org/spec"
# Domain vocabularies. prOnto/dapreco mirror the ontologies used in the OASIS
# DAPRECO GDPR formalization; repoint these to the official ontology IRIs in
# production. ex: is this project's local vocabulary for the remainder.
EX = "http://example.org/gdpr#"
PRONTO = "http://example.org/pronto#"
DAPRECO = "http://example.org/dapreco#"

NSMAP = {
    "lrml": LRML,
    "ruleml": RULEML,
    "ex": EX,
    "prOnto": PRONTO,
    "dapreco": DAPRECO,
}
# prefix used inside @iri attribute values -> declared namespace (for reference)
PREFIXES = {"ex:": EX, "prOnto:": PRONTO, "dapreco:": DAPRECO}


def _lrml(tag: str) -> str:
    return f"{{{LRML}}}{tag}"


def _ruleml(tag: str) -> str:
    return f"{{{RULEML}}}{tag}"


def _term(parent: etree._Element, term, keyed_vars: set[str]) -> None:
    """Render a Var or Ind. The first time a Var is seen it carries a @key so
    it can be referenced (e.g. by lrml:Bearer)."""
    if isinstance(term, Var):
        v = etree.SubElement(parent, _ruleml("Var"))
        if term.name not in keyed_vars:
            v.set("key", term.name)
            keyed_vars.add(term.name)
        v.text = term.name
    elif isinstance(term, Ind):
        i = etree.SubElement(parent, _ruleml("Ind"))
        i.text = term.name


def _formula(parent: etree._Element, f: Formula, keyed_vars: set[str]) -> None:
    """Recursively render Atom / And / Or."""
    if isinstance(f, Atom):
        atom = etree.SubElement(parent, _ruleml("Atom"))
        if f.comment:
            atom.append(etree.Comment(f" {f.comment} "))
        rel = etree.SubElement(atom, _ruleml("Rel"))
        rel.set("iri", f.iri)
        for a in f.args:
            _term(atom, a, keyed_vars)
    elif isinstance(f, And):
        node = etree.SubElement(parent, _ruleml("And"))
        for it in f.items:
            _formula(node, it, keyed_vars)
    elif isinstance(f, Or):
        node = etree.SubElement(parent, _ruleml("Or"))
        node.append(etree.Comment(" disjunction: 'given OR authorised' "))
        for it in f.items:
            _formula(node, it, keyed_vars)


def build(model=MODEL) -> etree._ElementTree:
    keyed_vars: set[str] = set()

    root = etree.Element(_lrml("LegalRuleML"), nsmap=NSMAP)
    root.addprevious(etree.Comment(
        "\n  OASIS LegalRuleML Core v1.0 representation of GDPR Article 8(2).\n"
        "  Every phrase of the provision is rendered as an explicit atom;\n"
        "  'given or authorised' is a ruleml:Or; the obligation names its\n"
        "  bearer via lrml:Bearer. See HOW_IT_WORKS.md for the full mapping.\n"
    ))

    # 1 - Legal source -------------------------------------------------------
    sources = etree.SubElement(root, _lrml("LegalSources"))
    src = etree.SubElement(sources, _lrml("LegalSource"))
    src.set("key", "ls_art8_2")
    src.set("sameAs", model.source_iri)

    # 2 - Prescriptive statement --------------------------------------------
    statements = etree.SubElement(root, _lrml("Statements"))
    statements.set("key", "stmts_art8_2")
    ps = etree.SubElement(statements, _lrml("PrescriptiveStatement"))
    ps.set("key", "ps_art8_2")

    # verbatim provision text
    para = etree.SubElement(ps, _lrml("Paraphrase"))
    para.text = model.verbatim

    rule = etree.SubElement(ps, _ruleml("Rule"))
    rule.set("closure", "universal")

    # IF: conditions (Art 8(1), "in such cases")
    if_el = etree.SubElement(rule, _ruleml("if"))
    if_el.append(etree.Comment(' triggering conditions ("in such cases" -> Art 8(1)) '))
    and_if = etree.SubElement(if_el, _ruleml("And"))
    for cond in model.conditions:
        _formula(and_if, cond, keyed_vars)

    # The bearer (controller) was already keyed in the IF conditions above,
    # so lrml:Bearer can reference it by #controller.

    # THEN: deontic modality + bearer + obliged content
    then_el = etree.SubElement(rule, _ruleml("then"))
    deontic = etree.SubElement(then_el, _lrml(model.modality))  # lrml:Obligation
    deontic.append(etree.Comment(f" normative modality: {model.modality} ('shall') "))
    bearer = etree.SubElement(deontic, _lrml("Bearer"))
    bearer.set("keyref", f"#{model.bearer}")
    bearer.append(etree.Comment(" bearer of the obligation: the controller "))
    _formula(deontic, model.obligation_content(), keyed_vars)

    # 3 - Association: bind rule to its legal source -------------------------
    assocs = etree.SubElement(root, _lrml("Associations"))
    assoc = etree.SubElement(assocs, _lrml("Association"))
    etree.SubElement(assoc, _lrml("appliesSource")).set("keyref", "#ls_art8_2")
    etree.SubElement(assoc, _lrml("toTarget")).set("keyref", "#ps_art8_2")

    return etree.ElementTree(root)


def write(path: str | pathlib.Path, model=MODEL) -> pathlib.Path:
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    build(model).write(
        str(path), xml_declaration=True, encoding="UTF-8", pretty_print=True
    )
    return path


if __name__ == "__main__":
    out = write("output/gdpr_art8_2.lrml.xml")
    print(f"Wrote {out}")
    print(etree.tostring(build(), pretty_print=True, encoding="unicode"))
