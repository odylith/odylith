# License And Attribution

Odylith is licensed under MIT.

Canonical license and attribution materials:

- [LICENSE](../LICENSE)
- [NOTICE](../NOTICE)
- [THIRD_PARTY_ATTRIBUTION.md](../THIRD_PARTY_ATTRIBUTION.md)

`LICENSE` is the canonical project license text. `NOTICE` carries the
project-level attribution identity used when redistributions preserve an
Odylith notice alongside the license. `THIRD_PARTY_ATTRIBUTION.md` tracks the
current runtime dependency closure and bundled managed-runtime supplier inputs.
The release pipeline publishes `THIRD_PARTY_ATTRIBUTION.md` as a standalone
asset and ships the same file inside the installed wheel metadata so Odylith
redistributions keep the consolidated third-party attribution with the product.
Odylith's MIT license applies to Odylith-authored code and materials. Any
redistributed third-party components remain under their own upstream licenses,
for example Apache-2.0, MIT, MPL-2.0, or BSD-family terms captured in
`THIRD_PARTY_ATTRIBUTION.md`.
Strict redistribution rule: Odylith can stay MIT, but any redistributed
LanceDB or Vespa code stays Apache-2.0, and any redistributed Tantivy code
stays MIT. This is a compliance engineering read, not legal advice.

Current shipping posture:

- LanceDB is in the shipped runtime inventory under Apache-2.0 and may be
  redistributed with Odylith only while preserving Apache-2.0 compliance
  materials and notices.
- Tantivy is in the shipped runtime inventory under MIT and may be
  redistributed with Odylith only while preserving the upstream MIT notice.
- Vespa is currently an optional external integration target in this repo, not
  a bundled runtime dependency. The repo ships Odylith-authored Vespa
  application-package/config assets, but not Vespa server software itself. If
  Odylith later bundles Vespa artifacts, those artifacts must be added to the
  third-party inventory and carried under Vespa's upstream license terms.

Odylith's license audit is fail-closed. Unknown licenses,
commercial/proprietary terms, and disallowed license families block the audit
until they are explicitly reviewed and accepted.
