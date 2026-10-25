# M1 device binding fix

The owner completed SMS verification, discovered two same-model L05C devices,
and identified the target through a changed device name. The fixed upstream
can map the selected MiNA device to the first MiIO entry sharing its model.
An explicit cloud deviceID alone therefore does not establish the TTS target.

Keep existing upstream services and protocols. Add a runtime speaker subclass
that changes only numeric MIOT DID resolution. Prefer consistent direct
numeric identifiers from the selected device; otherwise require its exact
name to be unique in both MiNA and MiIO lists. Reject absent/ambiguous matches,
conflicting identifiers/models and query failures. No model-only or list-order
fallback. Errors do not contain names, identifiers or raw server responses.

All automated tests use synthetic metadata and mocked service boundaries.
Real account/device calls and audible playback remain with the owner.

- [x] Reproduce the original wrong-target behavior offline and add regressions.
- [x] Implement and wire the narrow subclass; run both environments' suites.
- [x] Update M1 instructions/evidence; independently review and deliver a PR.

Independent review found no blocking issues and reran all 26 authentication /
binding tests successfully. The actual upstream subclass and lifespan class
lookup were verified with synthetic devices, without login or server startup.
Full regression: M0 56 passed / 4 skipped; optional environment 60 passed.
