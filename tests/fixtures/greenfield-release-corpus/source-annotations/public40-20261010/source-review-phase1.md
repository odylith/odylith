# Independent Public40 source review — phase 1

All 40 cases were read from `all-sources.json` before receiving or reading candidate annotations. No repository/product code, historic output, linked repository, dashboard, or holdout was read. No native product run or repository edit occurred.

Input file SHA-256: `aa6db335c70b18cc6957deb430d0f853db3b106d9932c6d6205899e32cc23047`.
Supplied aggregate source-case SHA-256 retained: `4606712fcee60cfd99e3e45ece28cadf60e899c8e71d7b8b573f6b3e13e383d2`.
Frozen census SHA-256: `b24cd14f7ba76ebc9c6a865843d78f1960a7e62ad5508398ba44149a1813cf66`.

All 40 case IDs are unique and preserve input ordering. All nonempty prompt/confirmed-intent hashes and all 40 combined evidence hashes verified. Full source texts are preserved verbatim in the census; every recorded quote span was checked against UTF-8 bytes.

## Independent outcome expectations

22 commit cases: 14 simple complete workflows and 8 explicit five-actor workflows. Of the latter, 4 include detailed reviewed intent, 9 safety boundaries each, and 3 explicitly non-material defaults each.

18 clarify cases: topic and repository evidence do not state a complete operator-authorized product task. Each census entry supplies one material question. A source description mentioning users, integrations, or capabilities does not resolve that missing task.

## Material adjudication boundaries

- Simple complete workflows are sufficient to commit. Do not demand domain richness, extra reviewers, or a new product decision when performer, work item, action, and verified result are already supplied.
- A resolution owner is an assigned role, with no separate action specified. The first-path performer is the service coordinator. Census retains the owner mention without inventing a second performer.
- Explicit five-system inventories do not create five additional first-path performers. System responsibilities remain mandatory support obligations.
- A compound actor turn is one ordered turn here. For example, opening a dossier and attaching sources is one supplied first-path turn with both actions required. Atomic action counting may differ legitimately if semantics and order survive.
- Source-backed recurring invalidation, privacy, lineage, and publication gates remain material obligations even when not enumerated in the first complete path. They are not extra first-path events.
- Accessibility conformance authorizes release-manager publication through its privacy boundary, although the first-path last step says verification. Preserve both publication closure and the five supplied path turns.
- Healthcare question registration and synthesis limitations are mandatory through actor duties, product systems, and proof. Do not invent a new human synthesis performer.
- Open-data requires exact read-only query, schema/row-count validation, and CKAN package/resource/portal identity. CKAN is product source context, but the source grants no live endpoint, credentials, or mandatory integration.
- All 12 explicit non-material ambiguities have supplied defaults and must not cause clarification.
- Repository metadata never grants runtime integration, data/code access, certification, scientific approval, ethics approval, or government authority.

## Counting and uncertainty

Semantic case-instance totals: 54 performing actor roles, 22 governed state objects, 40 product systems, 82 first-path actor turns, 48 explicit safety boundaries, plus one simple-case traceability constraint.

Counts use explicit units, not an invented universal atom count. Non-goals can overlap safety constraints; repeated source obligations are not silently counted as new path steps. The census records genuine interpretive uncertainties per case. No complexity band is claimed because the supplied band wrapper omits its tier helper.

## Per-case outcomes

| Case | Outcome | Actors | State objects | Product systems | Path turns | Material questions |
|---|---|---:|---:|---:|---:|---:|
| release-accessibility-004-topic | clarify | 0 | 0 | 0 | 0 | 1 |
| release-accessibility-005-source | commit | 5 | 1 | 5 | 5 | 0 |
| release-accessibility-006-source | clarify | 0 | 0 | 0 | 0 | 1 |
| release-accessibility-007-source | commit | 1 | 1 | 0 | 3 | 0 |
| release-agriculture-021-description | commit | 1 | 1 | 0 | 3 | 0 |
| release-agriculture-024-topic | clarify | 0 | 0 | 0 | 0 | 1 |
| release-agriculture-037-source | commit | 5 | 1 | 5 | 5 | 0 |
| release-agriculture-030-source | clarify | 0 | 0 | 0 | 0 | 1 |
| release-civic-tech-041-description | commit | 1 | 1 | 0 | 3 | 0 |
| release-civic-tech-044-topic | clarify | 0 | 0 | 0 | 0 | 1 |
| release-civic-tech-045-source | commit | 1 | 1 | 0 | 3 | 0 |
| release-civic-tech-057-source | commit | 5 | 1 | 5 | 5 | 0 |
| release-climate-061-description | commit | 1 | 1 | 0 | 3 | 0 |
| release-climate-064-topic | clarify | 0 | 0 | 0 | 0 | 1 |
| release-climate-073-source | commit | 5 | 1 | 5 | 5 | 0 |
| release-climate-069-source | commit | 1 | 1 | 0 | 3 | 0 |
| release-education-081-description | commit | 1 | 1 | 0 | 3 | 0 |
| release-education-084-topic | clarify | 0 | 0 | 0 | 0 | 1 |
| release-education-085-source | commit | 1 | 1 | 0 | 3 | 0 |
| release-education-086-source | clarify | 0 | 0 | 0 | 0 | 1 |
| release-healthcare-117-source | commit | 5 | 1 | 5 | 5 | 0 |
| release-healthcare-104-topic | clarify | 0 | 0 | 0 | 0 | 1 |
| release-healthcare-108-source | clarify | 0 | 0 | 0 | 0 | 1 |
| release-healthcare-109-source | commit | 1 | 1 | 0 | 3 | 0 |
| release-mobility-121-description | commit | 1 | 1 | 0 | 3 | 0 |
| release-mobility-124-topic | clarify | 0 | 0 | 0 | 0 | 1 |
| release-mobility-125-source | commit | 5 | 1 | 5 | 5 | 0 |
| release-mobility-126-source | clarify | 0 | 0 | 0 | 0 | 1 |
| release-open-data-142-topic | clarify | 0 | 0 | 0 | 0 | 1 |
| release-open-data-144-topic | clarify | 0 | 0 | 0 | 0 | 1 |
| release-open-data-157-source | commit | 5 | 1 | 5 | 5 | 0 |
| release-open-data-150-source | clarify | 0 | 0 | 0 | 0 | 1 |
| release-research-161-description | commit | 1 | 1 | 0 | 3 | 0 |
| release-research-163-description | commit | 1 | 1 | 0 | 3 | 0 |
| release-research-170-source | clarify | 0 | 0 | 0 | 0 | 1 |
| release-research-171-source | commit | 5 | 1 | 5 | 5 | 0 |
| release-security-182-topic | clarify | 0 | 0 | 0 | 0 | 1 |
| release-security-183-description | commit | 1 | 1 | 0 | 3 | 0 |
| release-security-186-source | clarify | 0 | 0 | 0 | 0 | 1 |
| release-security-195-source | commit | 1 | 1 | 0 | 3 | 0 |

Phase 1 is complete. Ready for a bounded phase 2 comparison; the independent expectations above remain frozen. This review is an independent source-only contribution, not a model score and not sole release semantic qualification. The final qualification contract still requires Astra or a comparably strong reviewer.
