# Validating against the official OASIS LegalRuleML schema

The pipeline's built-in validator (`src/validate.py`) checks XML well-formedness
plus structural conformance to the LegalRuleML content model (root/namespaces,
`PrescriptiveStatement > ruleml:Rule` with `if`/`then`, a deontic modality in the
conclusion, and `key`/`keyref` referential integrity). That runs with no external
files and is enough to demonstrate the rule is well-formed LegalRuleML.

For **full grammar validation** against the published OASIS schema, use the
official RELAX NG / XSD from the LegalRuleML Core Specification v1.0:

- Spec + schema deliverables: http://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/
- Repo: https://github.com/oasis-tcs/legalruleml

## Option A — RELAX NG with `jing`

```bash
# 1. download the RELAX NG schema (.rnc compact or .rng) into this folder
# 2. if you have the compact (.rnc) form, convert to .rng once with trang:
trang legalruleml.rnc legalruleml.rng
# 3. validate
jing legalruleml.rng ../output/gdpr_art8_2.lrml.xml
```

## Option B — RELAX NG with `xmllint` (libxml2)

```bash
xmllint --noout --relaxng legalruleml.rng ../output/gdpr_art8_2.lrml.xml
```

## Option C — XSD with `xmllint`

```bash
xmllint --noout --schema legalruleml.xsd ../output/gdpr_art8_2.lrml.xml
```

## Option D — through this project's validator

Drop a `.rng` or `.xsd` next to this file and point the pipeline at it:

```bash
python main.py --schema schema/legalruleml.rng
# or
LRML_SCHEMA=schema/legalruleml.rng python -m src.validate output/gdpr_art8_2.lrml.xml
```

> Note: the LegalRuleML grammar imports RuleML modules. Keep the referenced
> module files alongside the top-level schema so the include paths resolve, and
> make sure the namespace URIs in the XML (`lrml`, `ruleml`) match the schema
> version you validate against.
