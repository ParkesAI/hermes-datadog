"""Observable HTTP boundaries, using generated keys and synthetic Datadog events only."""

import hashlib
import hmac
import io
import json
import secrets
import unittest

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from hermes_datadog.receiver import MAX_BODY_BYTES, Settings, create_app


class ReceiverTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.secret = secrets.token_hex(32)
        self.deliveries = []
        self.upstream_status = 202
        self.redirect_followed = False

        async def upstream(request):
            body = await request.read()
            timestamp = request.headers["X-Webhook-Timestamp"]
            expected = hmac.new(
                self.secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
            ).hexdigest()
            self.assertEqual(request.headers["X-Webhook-Signature-V2"], expected)
            self.deliveries.append((body, dict(request.headers)))
            return web.json_response(
                {"status": "accepted"},
                status=self.upstream_status,
                headers={"Location": "/unexpected"} if self.upstream_status == 302 else {},
            )

        async def unexpected(request):
            self.redirect_followed = True
            return web.json_response({"status": "accepted"}, status=202)

        app = web.Application()
        app.router.add_post("/webhooks/datadog", upstream)
        app.router.add_route("*", "/unexpected", unexpected)
        self.backend = TestServer(app, host="127.0.0.1")
        await self.backend.start_server()
        self.addAsyncCleanup(self.backend.close)
        self.settings = Settings(
            secret=self.secret,
            monitor_ids=frozenset({"101"}),
            upstream_port=self.backend.port,
        )
        self.client = TestClient(TestServer(create_app(self.settings), host="127.0.0.1"))
        await self.client.start_server()
        self.addAsyncCleanup(self.client.close)
        self.body = json.dumps(
            {
                "monitor_id": 101,
                "event_id": "event-1",
                "transition": "Triggered",
                "scope": "service:example",
                "title": "Synthetic alert",
            },
            indent=2,
        ).encode()

    def headers(self, body=None, **extra):
        return {"Authorization": "Bearer " + self.secret, **extra}

    async def test_original_bytes_survive_and_identity_cannot_be_spoofed(self):
        for supplied_id in ["first-forged-id", "second-forged-id"]:
            response = await self.client.post(
                "/datadog",
                data=self.body,
                headers=self.headers(**{"X-GitHub-Delivery": supplied_id}),
            )
            self.assertEqual(response.status, 202)
        self.assertEqual(len(self.deliveries), 2)
        identity = json.dumps(
            ["101", "event-1", "Triggered", "service:example"], separators=(",", ":")
        )
        expected_id = "datadog-" + hashlib.sha256(identity.encode()).hexdigest()
        for body, headers in self.deliveries:
            self.assertEqual(body, self.body)
            self.assertEqual(headers["X-GitHub-Delivery"], expected_id)
            self.assertEqual(headers["X-GitHub-Event"], "datadog.monitor_alert")
            self.assertNotIn("Authorization", headers)

    async def test_missing_wrong_or_malformed_authorization_never_dispatches(self):
        for authorization in [None, "Bearer wrong", "Basic bad", "Bearer "]:
            headers = {} if authorization is None else {"Authorization": authorization}
            response = await self.client.post("/datadog", data=self.body, headers=headers)
            self.assertEqual(response.status, 401)
        self.assertFalse(self.deliveries)

    async def test_other_monitors_and_unsupported_transitions_are_ignored(self):
        baseline = json.loads(self.body)
        for change in [
            {"monitor_id": 202},
            {"monitor_id": True},
            {"monitor_id": {}},
            {"transition": "Warn"},
            {"transition": "No Data"},
            {"transition": "Renotify"},
        ]:
            response = await self.client.post(
                "/datadog", json={**baseline, **change}, headers=self.headers()
            )
            self.assertEqual(response.status, 200)
            self.assertEqual((await response.json())["status"], "ignored")
        self.assertFalse(self.deliveries)

    async def test_missing_or_malformed_identity_is_not_admitted(self):
        baseline = json.loads(self.body)
        for change in [
            {"event_id": None},
            {"event_id": ""},
            {"event_id": True},
            {"event_id": []},
            {"scope": []},
        ]:
            response = await self.client.post(
                "/datadog", json={**baseline, **change}, headers=self.headers()
            )
            self.assertEqual(response.status, 400)
        self.assertFalse(self.deliveries)

    async def test_recovery_and_group_have_distinct_delivery_identities(self):
        baseline = json.loads(self.body)
        for change in [
            {},
            {"title": "Edited title"},
            {"transition": "Recovered"},
            {"scope": "service:other"},
        ]:
            response = await self.client.post(
                "/datadog", json={**baseline, **change}, headers=self.headers()
            )
            self.assertEqual(response.status, 202)
        ids = [h["X-GitHub-Delivery"] for _, h in self.deliveries]
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(len(set(ids)), 3)

    async def test_invalid_json_fails_without_dispatch(self):
        for body in [b"not-json", b"[]", b"\xff"]:
            response = await self.client.post("/datadog", data=body, headers=self.headers(body))
            self.assertEqual(response.status, 400)
        self.assertFalse(self.deliveries)

    async def test_backend_errors_and_redirects_are_retryable_not_acknowledged(self):
        for status in [401, 429, 500, 302]:
            self.upstream_status = status
            response = await self.client.post("/datadog", data=self.body, headers=self.headers())
            self.assertEqual(response.status, 503)
        self.assertFalse(self.redirect_followed)

    async def test_backend_connection_failure_is_retryable(self):
        await self.backend.close()
        response = await self.client.post("/datadog", data=self.body, headers=self.headers())
        self.assertEqual(response.status, 503)

    async def test_size_limit_and_route_scope(self):
        body = b" " * (MAX_BODY_BYTES + 1)
        response = await self.client.post(
            "/datadog", data=io.BytesIO(body), headers=self.headers(body)
        )
        self.assertEqual(response.status, 413)
        self.assertEqual((await self.client.get("/datadog")).status, 405)
        self.assertEqual((await self.client.post("/other")).status, 404)
        response = await self.client.get("/health")
        self.assertEqual(await response.json(), {"status": "ok"})
        self.assertFalse(self.deliveries)


class SettingsTest(unittest.TestCase):
    def test_invalid_settings_fail_closed_and_secret_is_not_in_repr(self):
        secret = secrets.token_hex(32)
        valid = {"secret": secret, "monitor_ids": frozenset({"101"})}
        self.assertNotIn(secret, repr(Settings(**valid)))
        for update in [
            {"secret": ""},
            {"secret": "<dedicated bearer secret>"},
            {"monitor_ids": frozenset()},
            {"monitor_ids": frozenset({"not-an-id"})},
            {"host": "0.0.0.0"},
            {"port": 0},
            {"port": True},
            {"upstream_port": 8652},
            {"route": "../other"},
        ]:
            with self.subTest(fields=list(update)):
                with self.assertRaises(ValueError):
                    Settings(**{**valid, **update})


if __name__ == "__main__":
    unittest.main()
