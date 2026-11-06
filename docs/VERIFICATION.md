# Verification and compatibility

## Qualification target

Hermes Agent 0.23.0, commit `2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19`.

Qualification completed on 2026-11-06:

- Ten HTTP/settings tests pass on Python 3.11–3.14. Two lifecycle/native-signature
  tests pass against the pinned real Hermes SDK, both in CI and on the deployment
  runtime. Native plugin doctor passes without warnings.
- Native installation uses an immutable Git commit through Hermes's plugin manager.
  Wheel/source builds and metadata/content checks pass.
- Datadog's own Test Notifications flow sent an Alert and an Alert Recovery through
  the actual HTTPS endpoint. Both produced completed Hermes responses, distinguishing
  a test trigger from a recovery. Each model transcript contained one user message,
  one assistant response and zero tool calls.
- The provider test used an unsaved message draft containing only the new webhook
  recipient. The draft was cancelled; the original saved monitor query, thresholds,
  message and Slack recipient were verified unchanged afterward.
- The saved notification rule displayed the expected scoped coverage and separate
  Alert/OK routing to the new webhook. Billing monitors were excluded from rollout.
- An unsigned public POST returned 401. Public health returned 404. Receiver and native
  sockets bound only to loopback; existing private services stayed available.
- Source, distributions and Git history were scanned/reviewed for secrets and private
  deployment identifiers. Runtime configuration and private event data remain outside
  this repository.

This establishes provider-originated test delivery and completed analysis, not a
production incident, a load test or an independent security audit. Warning/no-data
filters, duplicate identity, grouped/recovery identity and backend failure handling
are exercised by HTTP tests. Native duplicate retention owns suppression; exactly-once
execution across failures and replay protection after native records expire are not
claimed. Inbound authentication is a bearer secret over HTTPS, not a Datadog body HMAC.

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
