# Security policy

Report vulnerabilities with GitHub's private **Report a vulnerability** feature.
Never post real credentials, private monitor payloads or deployment settings in
public issues. Security fixes target the latest released version.

The plugin runs in-process inside Hermes; it is not a sandbox. Review and pin the
source. Publish only `/datadog` through HTTPS and keep the loopback receiver, health,
native webhook listener and dashboard private. Apply ingress rate/body limits.

Datadog sends a dedicated bearer credential in a custom header. Constant-time
comparison authenticates it before the body is parsed. This is not a per-request
Datadog body signature or timestamp-bound freshness guarantee. Anyone holding the
secret can submit payloads as the sender. Protect the ingress/TLS termination,
Datadog hidden variable, private Hermes configuration and backups. Do not log the
Authorization header. Rotate Datadog and Hermes values together.

An explicit monitor allowlist and transition filter apply before forwarding. Payload
fields are untrusted data, not instructions. Keep the native agent's permissions
narrow and review downstream session storage and model-provider retention.

Only the original body and freshly generated native V2 signature/identity headers
are forwarded to a fixed loopback endpoint. The bearer header is not forwarded.
Event identity uses authenticated monitor/event/transition/scope fields, not caller
delivery headers. Native Hermes owns durable admission, duplicate retention and
execution. Replays can be accepted after native records expire; this receiver adds
no independent queue or exactly-once guarantee across failures.

No private hostnames, organization/project identities, signing keys or deployment
payloads belong in the source repository or release artifacts. See the verification
record for the qualified Hermes version and material test limitations.
