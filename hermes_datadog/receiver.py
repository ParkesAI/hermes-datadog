"""Datadog bearer authentication and a bounded bridge to native Hermes webhooks."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import time
from dataclasses import dataclass, field

from aiohttp import ClientError, ClientSession, ClientTimeout, web

LOG = logging.getLogger(__name__)
CLIENT = web.AppKey("upstream_client", ClientSession)
MAX_BODY_BYTES = 1_048_576


@dataclass(frozen=True)
class Settings:
    secret: str = field(repr=False)
    monitor_ids: frozenset[str]
    host: str = "127.0.0.1"
    port: int = 8652
    upstream_port: int = 8644
    route: str = "datadog"
    profile: str | None = None

    def __post_init__(self):
        if (
            not isinstance(self.secret, str)
            or len(self.secret) < 32
            or any(c.isspace() or c in "<>" for c in self.secret)
        ):
            raise ValueError("A Datadog bearer secret of at least 32 characters is required")
        if not self.monitor_ids or any(
            not isinstance(p, str) or not re.fullmatch(r"[0-9]+", p) for p in self.monitor_ids
        ):
            raise ValueError("Provide an explicit allowlist of numeric Datadog monitor IDs")
        if self.host not in {"127.0.0.1", "::1"}:
            raise ValueError("The receiver must bind to a loopback address")
        for port in (self.port, self.upstream_port):
            if type(port) is not int or not 1 <= port <= 65535:
                raise ValueError("Ports must be integers from 1 to 65535")
        if self.port == self.upstream_port:
            raise ValueError("Receiver and native webhook ports must differ")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", self.route):
            raise ValueError("Invalid native webhook route name")

        if self.profile is not None and (
            not isinstance(self.profile, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", self.profile)
        ):
            raise ValueError("Invalid target profile name")

    @property
    def upstream_url(self) -> str:
        prefix = f"/p/{self.profile}" if self.profile is not None else ""
        return f"http://127.0.0.1:{self.upstream_port}{prefix}/webhooks/{self.route}"


def create_app(settings: Settings) -> web.Application:
    """Own the HTTP client for exactly the lifetime of this receiver."""
    app = web.Application(client_max_size=MAX_BODY_BYTES)

    async def client_lifecycle(app):
        async with ClientSession(timeout=ClientTimeout(total=5), trust_env=False) as client:
            app[CLIENT] = client
            yield

    async def health(request):
        return web.json_response({"status": "ok"})

    async def receive(request):
        authorization = request.headers.get("Authorization", "").encode("utf-8")
        expected = ("Bearer " + settings.secret).encode("utf-8")
        if not hmac.compare_digest(authorization, expected):
            return web.json_response({"error": "invalid authorization"}, status=401)
        body = await request.read()
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            return web.json_response({"error": "invalid JSON"}, status=400)
        if not isinstance(payload, dict):
            return web.json_response({"error": "expected a JSON object"}, status=400)
        monitor = payload.get("monitor_id")
        if type(monitor) not in (str, int) or str(monitor) not in settings.monitor_ids:
            return web.json_response({"status": "ignored", "reason": "monitor not allowed"})
        transition = payload.get("transition")
        if transition not in ("Triggered", "Re-Triggered", "Recovered"):
            return web.json_response({"status": "ignored", "reason": "unsupported transition"})
        event = payload.get("event_id")
        scope = payload.get("scope", "")
        if type(event) not in (str, int) or not str(event).strip() or len(str(event)) > 256:
            return web.json_response({"error": "event_id is required"}, status=400)
        if not isinstance(scope, str):
            return web.json_response({"error": "scope must be a string"}, status=400)
        identity = json.dumps([str(monitor), str(event), transition, scope], separators=(",", ":"))
        # Preserve original bytes; derive identity from the authenticated event, never caller headers.
        timestamp = str(int(time.time()))
        native_signature = hmac.new(
            settings.secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature-V2": native_signature,
            "X-Webhook-Timestamp": timestamp,
            "X-GitHub-Event": "datadog.monitor_alert",
            "X-GitHub-Delivery": "datadog-" + hashlib.sha256(identity.encode()).hexdigest(),
        }
        try:
            async with app[CLIENT].post(
                settings.upstream_url, data=body, headers=headers, allow_redirects=False
            ) as response:
                if response.status >= 300:
                    LOG.warning("Native webhook receiver returned HTTP %s", response.status)
                    return web.json_response({"error": "native receiver unavailable"}, status=503)
                # Acceptance is not agent completion; native Hermes owns durable processing.
                return web.json_response({"status": "accepted"}, status=202)
        except (ClientError, TimeoutError):
            LOG.warning("Native webhook receiver unavailable")
            return web.json_response({"error": "native receiver unavailable"}, status=503)

    app.cleanup_ctx.append(client_lifecycle)
    app.router.add_get("/health", health)
    app.router.add_post("/datadog", receive)
    return app
