# GDPR Article 8(2) → OASIS LegalRuleML

A small, runnable project that turns a real legal provision — **GDPR Article 8(2)**
— into a machine-readable **OASIS LegalRuleML** rule, following the OASIS standard
and the structure shown in the official use-case example.

It is the demo task end-to-end:

```
fetch (gdpr-info.eu)  →  identify entities  →  build LegalRuleML  →  validate
```

---

## What it produces

| Output file | What it is |
|---|---|
| `output/article_8.json` | the provision text, fetched & parsed |
| `output/gdpr_art8_2.lrml.xml` | the LegalRuleML rule for Art 8(2) |
| `output/validation_report.txt` | the validation result |

---

## Run it in VS Code

1. Open this folder in VS Code (`File → Open Folder…`). Accept the recommended
   extensions (Python + Red Hat XML).
2. **Terminal → Run Task… → “Setup: create venv + install deps”** (one time).
3. Press **F5** and choose **“Run pipeline (live fetch)”**
   — or Run Task → “Run: full pipeline”.

No internet? Use **“Run pipeline (offline / cached)”** — it uses the bundled
verbatim copy of Article 8 in `data/`.

### Or from a terminal

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py            # live fetch, auto-falls back to cache if blocked/offline
python main.py --offline  # force the cached provision text
```

---

## How the demo requirements are met

**1. Identify actor, action, conditions, normative modality** — `src/entities.py`
holds the hand-authored analysis of Art 8(2):

| Element | Value |
|---|---|
| Actor / bearer | the **controller** |
| Modality | **Obligation** (deontic “shall”) |
| Action | `makeReasonableEffortsToVerifyParentalConsent(controller, child, availableTechnology)` |
| Conditions (“in such cases”, from Art 8(1)) | controller · child · service offered directly to child · processing based on consent · child below consent age |
| Qualifier | “taking into consideration available technology” |
| Exceptions | none stated in 8(2) |

**2. The LegalRuleML XML** — `src/build_legalruleml.py` builds it from that model.
Structure:

```
lrml:LegalRuleML
 ├─ lrml:LegalSources          provenance → the gdpr-info.eu provision
 ├─ lrml:Statements
 │   └─ lrml:PrescriptiveStatement        (a norm, not a fact/definition)
 │        └─ ruleml:Rule  closure="universal"
 │             ├─ ruleml:if   → ruleml:And( condition atoms )
 │             └─ ruleml:then → lrml:Obligation( action atom )
 └─ lrml:Associations          binds the rule back to its LegalSource
```

**3. Technical explanation of the main elements**

- **`lrml:LegalSource`** — records *which* provision is encoded (its `sameAs`
  points at the gdpr-info.eu URL), so every rule is traceable to the law.
- **`lrml:PrescriptiveStatement`** — marks the content as a *norm* (prescribes
  behaviour), distinct from `FactualStatement` or `ConstitutiveStatement`.
- **`ruleml:Rule` + `ruleml:if`/`ruleml:then`** — the logical core: a
  universally-quantified implication (`closure="universal"` = “for all
  controllers/children …”).
- **`ruleml:And` of `ruleml:Atom`** — the triggering conditions. Each `Atom` is a
  `ruleml:Rel` (predicate) over `ruleml:Var` (variables) / `ruleml:Ind`
  (individual constants).
- **`lrml:Obligation`** — the **normative modality**. Wrapping the conclusion atom
  in `Obligation` is what makes this a *duty* rather than a permission or a plain
  fact. (Swap for `lrml:Permission` / `lrml:Prohibition` / `lrml:Right` for other
  provisions.)
- **actor & action** — the actor is the first argument of the obligation atom
  (`controller`); the action is the predicate itself; `availableTechnology`
  carries the statute’s qualifier.
- **`lrml:Association`** (`appliesSource` → `toTarget`) — formally links the rule
  to its legal source.

**4. Validation** — `src/validate.py`, run automatically as Step 4. Two tiers:

- *Built-in* (no external files): well-formedness + structural conformance to the
  LegalRuleML content model + `key`/`keyref` referential integrity.
- *Official schema* (optional): point it at the OASIS RELAX NG / XSD —
  `python main.py --schema schema/legalruleml.rng`. See `schema/README.md` for the
  `jing` / `xmllint` commands and where to get the schema.

---

## Notes for the production version

- Domain predicates use a placeholder namespace `ex:` (`http://example.org/gdpr#`).
  In a real build these map to established vocabularies — e.g. the `prOnto` /
  `rioOnto` ontologies used in the OASIS DAPRECO use case.
- LegalRuleML offers richer constructs we can add on request: `lrml:Bearer` to name
  the actor explicitly, `lrml:Context` to tag modality externally (DAPRECO style),
  and `ruleml:Naf` for defeasible exceptions.

## Project layout

```
gdpr-legalruleml-demo/
├─ main.py                 pipeline orchestrator (CLI)
├─ requirements.txt
├─ data/art8_cached.json   bundled verbatim Article 8 (offline fallback)
├─ src/
│  ├─ fetch_article.py     Step 1 – fetch + parse from gdpr-info.eu
│  ├─ entities.py          Step 2 – normative model of Art 8(2)
│  ├─ build_legalruleml.py Step 3 – build the LegalRuleML XML
│  └─ validate.py          Step 4 – validate
├─ schema/README.md        how to run official OASIS-schema validation
├─ output/                 generated artifacts
└─ .vscode/                run/debug/tasks config
```

Source of the provision: https://gdpr-info.eu/art-8-gdpr/ ·
Standard: OASIS LegalRuleML Core Specification v1.0 ·
Example followed: `oasis-tcs/legalruleml` use case #1.
# LegalRuleML
