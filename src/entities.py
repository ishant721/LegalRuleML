"""
Step 2 - Identify the normative elements of GDPR Article 8(2), fully decomposed.

This is the *modeling analysis* the demo asks for: actor, action, conditions,
normative modality, object, parties, qualifier, exceptions. It is done by hand
(a human reading the provision) and encoded here as a small formula tree so the
XML builder can render it deterministically.

Provision (Art 8(2), verbatim from gdpr-info.eu):
  "The controller shall make reasonable efforts to verify in such cases that
   consent is given or authorised by the holder of parental responsibility
   over the child, taking into consideration available technology."

Every phrase of the sentence is given its own atom so the LegalRuleML is a
faithful representation, not a coarse paraphrase:

  "The controller"                          -> Controller(controller)   [bearer]
  "shall"                                    -> lrml:Obligation
  "make reasonable efforts"                  -> ReasonableEffort(effort) + makesEffort(controller, effort)
  "to verify"                                -> hasPurposeToVerify(effort, consent)
  "that consent"                             -> Consent(consent)
  "is given or authorised"                   -> Or( givenBy(consent,holder), authorisedBy(consent,holder) )
  "by the holder of parental responsibility" -> HolderOfParentalResponsibility(holder, child)
  "over the child"                           -> child (also DataSubject(child))
  "taking into consideration available technology"
                                             -> takesIntoConsideration(effort, availableTechnology)
  "in such cases" (-> Art 8(1))              -> the condition atoms below
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Union


# --------------------------------------------------------------------------- #
# A tiny formula model: Atom / And / Or over Var / Ind terms.                  #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Ind:
    name: str


Term = Union[Var, Ind]


@dataclass(frozen=True)
class Atom:
    iri: str
    args: List[Term]
    comment: str = ""


@dataclass(frozen=True)
class And:
    items: List["Formula"]


@dataclass(frozen=True)
class Or:
    items: List["Formula"]


Formula = Union[Atom, And, Or]


# --------------------------------------------------------------------------- #
# The hand-authored model of Article 8(2).                                    #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Art8_2Model:
    source_iri: str = "https://gdpr-info.eu/art-8-gdpr/"
    provision: str = "GDPR Article 8(2)"
    verbatim: str = (
        "The controller shall make reasonable efforts to verify in such cases "
        "that consent is given or authorised by the holder of parental "
        "responsibility over the child, taking into consideration available "
        "technology."
    )

    # Normative modality: "shall" -> Obligation
    modality: str = "Obligation"
    # Bearer of the obligation (the deontic lrml:Bearer).
    bearer: str = "controller"

    # --- IF: triggering conditions ("in such cases" -> carried from Art 8(1))
    conditions: List[Atom] = field(default_factory=lambda: [
        Atom("prOnto:Controller", [Var("controller")],
             "the actor is a data controller"),
        Atom("prOnto:DataSubject", [Var("child")],
             "the data subject is the child"),
        Atom("ex:Child", [Var("child")],
             "the data subject is a minor (child)"),
        Atom("ex:InformationSocietyService", [Var("service")],
             "an information society service"),
        Atom("ex:offeredDirectlyToChild", [Var("service"), Var("child")],
             "offered directly to the child (Art 8(1))"),
        Atom("prOnto:PersonalDataProcessing",
             [Var("processing"), Var("controller"), Var("child")],
             "processing of the child's personal data"),
        Atom("ex:basedOnConsent", [Var("processing")],
             "processing relies on consent as legal basis (Art 6(1)(a))"),
        Atom("ex:belowConsentAge", [Var("child")],
             "the child is below the applicable consent age (Art 8(1))"),
    ])

    # --- THEN: the content the controller is OBLIGED to bring about.
    # "make reasonable efforts to verify that consent is given or authorised
    #  by the holder of parental responsibility over the child, taking into
    #  consideration available technology."
    def obligation_content(self) -> Formula:
        return And([
            Atom("ex:ReasonableEffort", [Var("effort")],
                 "a reasonable effort"),
            Atom("ex:makesEffort", [Var("controller"), Var("effort")],
                 "the controller makes that effort"),
            Atom("ex:hasPurposeToVerify", [Var("effort"), Var("consent")],
                 "the effort's purpose is to verify the consent"),
            Atom("ex:takesIntoConsideration",
                 [Var("effort"), Ind("availableTechnology")],
                 "considering available technology"),
            Atom("ex:AvailableTechnology", [Ind("availableTechnology")],
                 "available technology"),
            Atom("prOnto:Consent", [Var("consent")],
                 "the consent in question"),
            Atom("ex:HolderOfParentalResponsibility",
                 [Var("holder"), Var("child")],
                 "the holder of parental responsibility over the child"),
            Or([
                Atom("dapreco:givenBy", [Var("consent"), Var("holder")],
                     "consent is GIVEN by the holder ..."),
                Atom("dapreco:authorisedBy", [Var("consent"), Var("holder")],
                     "... OR authorised by the holder"),
            ]),
        ])

    # --- Exceptions: none stated within Art 8(2) itself.
    exceptions: List[str] = field(default_factory=list)


MODEL = Art8_2Model()


# --------------------------------------------------------------------------- #
# Human-readable summary (used by main.py Step 2).                            #
# --------------------------------------------------------------------------- #
def _fmt_term(t: Term) -> str:
    return t.name


def _fmt(f: Formula, indent: int = 0) -> List[str]:
    pad = "    " + "  " * indent
    if isinstance(f, Atom):
        args = ", ".join(_fmt_term(a) for a in f.args)
        return [f"{pad}{f.iri}({args})"]
    if isinstance(f, And):
        out = [f"{pad}AND"]
        for it in f.items:
            out += _fmt(it, indent + 1)
        return out
    if isinstance(f, Or):
        out = [f"{pad}OR"]
        for it in f.items:
            out += _fmt(it, indent + 1)
        return out
    return []


def summary() -> str:
    m = MODEL
    lines = [
        f"Provision : {m.provision}",
        f"Source    : {m.source_iri}",
        f"Modality  : {m.modality}  (deontic 'shall')",
        f"Bearer    : {m.bearer}  (who the obligation falls on)",
        "Conditions (IF - 'in such cases' -> Art 8(1)):",
    ]
    for c in m.conditions:
        args = ", ".join(a.name for a in c.args)
        lines.append(f"    {c.iri}({args})  # {c.comment}")
    lines.append("Obligation content (THEN):")
    lines += _fmt(m.obligation_content(), 0)
    lines.append(f"Exceptions: {m.exceptions or 'none stated in Art 8(2)'}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(summary())
