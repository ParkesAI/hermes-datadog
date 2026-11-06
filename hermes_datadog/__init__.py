"""An installable Datadog ingress platform for Hermes Agent."""


def register(ctx):
    from .adapter import DatadogAdapter

    ctx.register_platform(
        name="datadog",
        label="Datadog webhooks",
        adapter_factory=DatadogAdapter,
        check_fn=lambda: True,
        install_hint="Configure a Datadog bearer secret and allowed monitor IDs",
        dashboard_description="Receive authenticated Datadog monitor webhooks on loopback",
        emoji="🚨",
    )
