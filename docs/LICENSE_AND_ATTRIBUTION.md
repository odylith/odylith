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

Odylith's license audit is fail-closed. Unknown licenses,
commercial/proprietary terms, and disallowed license families block the audit
until they are explicitly reviewed and accepted.
