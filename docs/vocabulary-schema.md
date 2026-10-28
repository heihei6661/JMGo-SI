# Vocabulary & Ledger Schema

The full ledgers are proprietary. The schema and import format are open so
teams can add domain terms without touching the core.

## Entry

```json
{
  "surface": "抓取",
  "lemma": "抓取",
  "pos": "VERB",
  "lang": "zh",
  "aliases": ["拿起", "夹取"],
  "domain": "robot-manipulation",
  "source": "internal",
  "license": "proprietary",
  "confidence": 0.9,
  "updated": "2026-10-28"
}
```

Required: `surface`, `pos`, `lang`. Everything else is optional.

## Import formats

**JSONL** (one entry per line) — recommended.

**TSV**:

```
surface<TAB>pos<TAB>lang<TAB>aliases(comma)<TAB>domain
```

Imports are validated against the schema; invalid rows are rejected with a
line number, never silently dropped.

## Ledger categories

| Ledger | Contents | Distribution |
|---|---|---|
| `general` | common words, grammar | seed subset open |
| `domain` | robot/industry terms | customer-supplied, private |
| `geo` | place names | third-party license |
| `learned` | grown from usage | private, never published |

## Licensing

- UD treebanks, GeoNames and zhconv keep their original licenses.
- Do not mark third-party data as proprietary.
- Customer-supplied domain terms remain the customer's; do not merge them into
  a shared/public ledger without permission.

## Privacy

Learned ledgers may contain user text. Treat them as personal data: local by
default, no upload, deletion on request.
