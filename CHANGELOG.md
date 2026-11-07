# Changelog

## 0.1.1 — 2026-11-07

- Optional target profile forwards signed deliveries to Hermes's native
  profile-prefixed webhook URL. Omission preserves the default-profile behavior.
- Validate profile names before constructing URLs; no fallback when the configured
  destination is unavailable. Authentication and payload bytes are unchanged.

## 0.1.0 — 2026-11-06

- Initial authenticated Datadog monitor ingress with explicit monitor and transition
  filters, loopback-only binding, native timestamped V2 forwarding and event identities.
- Native Hermes plugin and standard wheel packaging; MIT licensing, security policy,
  setup/removal guides, HTTP regression coverage and pinned real-SDK CI.
- Qualified with provider-originated Datadog alert and recovery tests through the
  real gateway to completed, tool-free agent analyses; existing notification routing
  and monitor definitions remained intact.
