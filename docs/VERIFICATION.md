# Verification and compatibility

## Qualification target

Hermes Agent 0.23.0, commit `2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19`.

The initial release is under qualification. Passing unit tests or obtaining HTTP
202 does not establish a real Datadog delivery or a completed Hermes response.

## Release checks

1. Run locked setup, lint, formatting, all tests, builds and distribution checks.
2. Verify native plugin discovery and a clean wheel installation. Confirm metadata,
   manifest, version and MIT licensing agree.
3. Run lifecycle/native-signature tests against the pinned real Hermes SDK.
4. Install an immutable candidate through Hermes's plugin manager. Configure only
   protected local credentials and explicit monitor/transition scope.
5. Send a controlled provider notification and inspect its actual Hermes result.
6. Verify authorization rejection, monitor filters, event identity, distinct groups
   and recoveries, retryable backend failure, redirect refusal and cleanup.
7. Confirm only the intended HTTPS path is public and other services remain private.
8. Scan source, history and distributions for secrets/deployment identifiers. Release
   immutable artifacts/checksums only after CI and qualification pass. Record remaining limits.

## Benchmarks and provenance

This receiver derives from the MIT-licensed
[Hermes Sentry](https://github.com/ParkesAI/hermes-sentry) packaging, lifecycle,
loopback bridge and verification approach. Its inbound authentication and event
contract are specific to Datadog. It does not claim that Datadog signs each body.

[Official Hermes plugins](https://github.com/NousResearch/hermes-official-plugins)
provide the native plugin API/manifest reference. Datadog's official Webhooks and
Notification Rules documentation define the provider configuration. These are
implementation references, not independent security endorsements.
