from uuid import UUID

import anyio
import httpx

from diddi_support.infrastructure.context.http import HttpContextProvider

RESOURCE_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


async def _test_food_and_send_use_the_same_context_contract() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        service = request.headers["x-support-context-scope"].split(":", 1)[0]
        resource_type = request.url.path.split("/")[-3]
        return httpx.Response(
            200,
            json={
                "protocol": "diddi.context.v1",
                "origin_service": service,
                "resource_type": resource_type,
                "resource_id": str(RESOURCE_ID),
                "data": {"status": "active"},
            },
        )

    for service, resource_type in (("diddifood", "order"), ("diddisend", "delivery")):
        provider = HttpContextProvider(
            base_url="https://owner.example.test",
            scope=f"{service}:support-context:read",
            transport=httpx.MockTransport(handler),
        )
        context = await provider.fetch(
            resource_type=resource_type,
            resource_id=RESOURCE_ID,
            request_id="req",
        )
        assert context.origin_service == service
        assert context.resource_type == resource_type


def test_food_and_send_use_the_same_context_contract() -> None:
    anyio.run(_test_food_and_send_use_the_same_context_contract)
