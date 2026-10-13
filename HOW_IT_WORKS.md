# GDPR Article 8(2) → LegalRuleML: method, formatting, and verification

This document answers three questions for the demo:

1. **Which rules were used to identify the elements** of the provision.
2. **How those elements were formatted into LegalRuleML XML.**
3. **How to verify the result.**

The provision (verbatim, from the client source https://gdpr-info.eu/art-8-gdpr/):

> "The controller shall make reasonable efforts to verify in such cases that
> consent is given or authorised by the holder of parental responsibility over
> the child, taking into consideration available technology."

---

## 1. The rules used to identify the elements

Identification is a **manual legal-reading step** (not automatic extraction). Each
element is found by applying one fixed rule to the sentence. The phrase that
triggers each rule is quoted from the text.

| # | Rule applied | Trigger phrase in Art 8(2) | Element identified |
|---|---|---|---|
| R1 | **Modality rule** — find the deontic/modal verb. *shall/must* ⇒ Obligation; *may* ⇒ Permission; *shall not* ⇒ Prohibition; *has the right to* ⇒ Right. | "**shall**" | Modality = **Obligation** |
| R2 | **Actor rule** — the grammatical subject of the modal verb is the bearer of the norm. | "**The controller**" | Actor = **controller** |
| R3 | **Action rule** — the main verb phrase governed by the modal is the required action. | "**make reasonable efforts to verify**" | Action predicate |
| R4 | **Condition rule** — antecedent clauses and cross-references define *when* the norm applies; resolve anaphora. | "**in such cases**" (points back to Art 8(1)) | Conditions = service offered directly to a child · consent-based processing (Art 6(1)(a)) · child below the consent age |
| R5 | **Object rule** — the clause the action operates on. | "**that consent is given or authorised**" | Object = parental consent |
| R6 | **Party rule** — other named legal persons in the clause. | "**the holder of parental responsibility**", "**the child**" | Auxiliary party + data subject |
| R7 | **Qualifier rule** — adverbial/standard clauses that bound the action (not a separate duty). | "**taking into consideration available technology**" | Qualifier on the action |
| R8 | **Exception rule** — look for *unless / except / shall not apply*. If none, the norm is non-defeasible here. | (none in 8(2)) | No exception |
| R9 | **Provenance rule** — record which provision is being encoded. | Article 8(2) | Legal source |

**The two judgement calls worth highlighting** (they show legal reading, not just grammar):
- **R1:** "shall" is the obligation marker.
- **R4:** "in such cases" is a cross-reference — it must be expanded into the
  Article 8(1) conditions, otherwise the rule's trigger is incomplete.

Result:

```
Modality : Obligation            (R1 ← "shall")
Actor    : controller            (R2 ← "The controller")
Action   : makeReasonableEffortsToVerifyParentalConsent(controller, child, availableTechnology)
Conditions (R4 ← "in such cases" → Art 8(1)):
   - Controller(controller)
   - Child(child)
   - offersServiceDirectlyToChild(controller, child)
   - processingBasedOnConsent(controller, child)
   - belowConsentAge(child)
Qualifier: available technology   (R7)
Exception: none                   (R8)
Source   : GDPR Art 8(2)          (R9)
```

In the code this analysis lives in `src/entities.py` (`Art8_2Model`).

---

## 2. How the elements are formatted into LegalRuleML XML

Each identified element maps to a specific LegalRuleML / RuleML construct. The
builder (`src/build_legalruleml.py`) applies this mapping deterministically.

Every phrase becomes an **explicit atom** (no meaning is hidden inside a
predicate name), the **"given or authorised"** disjunction uses `ruleml:Or`, and
the **actor** is named with the deontic `lrml:Bearer`.

| Identified element | LegalRuleML construct | Role |
|---|---|---|
| Legal source (R9) | `lrml:LegalSource` (`sameAs` = the gdpr-info.eu URL) | provenance |
| Verbatim text | `lrml:Paraphrase` | the human-readable provision |
| The norm itself | `lrml:PrescriptiveStatement` | marks it as a *norm* (not a fact/definition) |
| Rule body | `ruleml:Rule closure="universal"` | "for all controllers/children …" |
| Conditions (R4) | `ruleml:if` → `ruleml:And` of `ruleml:Atom` | the trigger (Art 8(1)) |
| Modality (R1) | `lrml:Obligation` | makes it a duty vs. permission/prohibition |
| Actor (R2) | `lrml:Bearer keyref="#controller"` | who the obligation falls on |
| Action (R3) | `ex:ReasonableEffort` + `ex:makesEffort` + `ex:hasPurposeToVerify` | reasonable effort, made by controller, to verify |
| Object (R5) | `prOnto:Consent` + `ruleml:Or(dapreco:givenBy, dapreco:authorisedBy)` | consent, given **or** authorised |
| Party (R6) | `ex:HolderOfParentalResponsibility(holder, child)` | the holder, over the child |
| Qualifier (R7) | `ex:takesIntoConsideration(effort, availableTechnology)` + `ex:AvailableTechnology` | the "available technology" standard |
| Each predicate / term | `ruleml:Rel iri="…"` over `ruleml:Var` / `ruleml:Ind` | relations and arguments |
| Source ↔ rule link | `lrml:Association` (`appliesSource` → `toTarget`) | binds the rule to the law |

Resulting shape:

```
lrml:LegalRuleML
 ├─ lrml:LegalSources
 │   └─ lrml:LegalSource  key="ls_art8_2"  sameAs=".../art-8-gdpr/"
 ├─ lrml:Statements
 │   └─ lrml:PrescriptiveStatement  key="ps_art8_2"
 │        ├─ lrml:Paraphrase  "<verbatim Art 8(2) text>"
 │        └─ ruleml:Rule  closure="universal"
 │             ├─ ruleml:if   → ruleml:And( 8 condition atoms )          ← R4
 │             └─ ruleml:then → lrml:Obligation                         ← R1
 │                                ├─ lrml:Bearer #controller            ← R2
 │                                └─ ruleml:And(
 │                                     ReasonableEffort, makesEffort,   ← R3
 │                                     hasPurposeToVerify, Consent,     ← R5
 │                                     takesIntoConsideration, AvailableTechnology, ← R7
 │                                     HolderOfParentalResponsibility,  ← R6
 │                                     ruleml:Or( givenBy, authorisedBy ) )  ← R5
 └─ lrml:Associations
     └─ lrml:Association  appliesSource=#ls_art8_2  toTarget=#ps_art8_2   ← R9
```

The full output is `output/gdpr_art8_2.lrml.xml`.

Naming note: predicates use `prOnto:` / `dapreco:` prefixes to mirror the
ontologies used in the OASIS DAPRECO GDPR formalization, plus a local `ex:`
vocabulary for the rest. The namespace IRIs are placeholders
(`http://example.org/…`); repoint them to the official ontology IRIs in
production.

---

## 3. How to verify it

Four levels, from quickest to most authoritative. Levels 1–2 run with no
external files; level 3 is the official-standard check; level 4 is semantic.

### Level 1 — well-formed XML
```bash
xmllint --noout output/gdpr_art8_2.lrml.xml
```
(or just open it in VS Code with the Red Hat XML extension — errors show inline.)

### Level 2 — structural conformance (built-in validator)
```bash
python -m src.validate output/gdpr_art8_2.lrml.xml
```
Checks the LegalRuleML content model: correct root + namespaces, a
`PrescriptiveStatement > ruleml:Rule` with `if`/`then`, a real deontic modality
in the conclusion, and that every `keyref` resolves to a defined `key`
(referential integrity). Prints `RESULT: VALID`.

### Level 3 — official OASIS schema (RELAX NG / XSD)
Download the LegalRuleML schema from the OASIS spec deliverables
(`http://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/`), then:
```bash
jing legalruleml.rng output/gdpr_art8_2.lrml.xml
# or
xmllint --noout --relaxng legalruleml.rng output/gdpr_art8_2.lrml.xml
# or through this project:
python main.py --schema schema/legalruleml.rng
```
See `schema/README.md` for the full steps.

### Level 4 — semantic faithfulness (real text vs XML), automated
```bash
python -m src.compare output/gdpr_art8_2.lrml.xml
```
This maps **every phrase** of Art 8(2) to the predicate/construct that must
appear in the XML and checks each one is present, printing a coverage table and
`RESULT: FULLY FAITHFUL` (18/18). It is also run automatically as Step 5 of
`main.py`. A human round-trip read and a reasoner run (checking the rule fires
on test facts, e.g. a 14-year-old user) are the remaining manual confirmations.

Levels 1–3 prove it is *correct LegalRuleML*; levels 4 prove it is *the right
LegalRuleML* for the provision.
