import asyncio
import os

from aiohttp import ClientSession, WSMsgType, web


BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://127.0.0.1:8501")
BACKEND_PREFIXES = (
    "/api/",
    "/admin/",
    "/cart/",
    "/chat",
    "/items",
    "/manager/",
    "/orders",
    "/products",
    "/recommendations/",
    "/users",
)


def upstream_for(path: str) -> str:
    if any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in BACKEND_PREFIXES):
        return BACKEND_URL
    return STREAMLIT_URL


async def proxy_http(request: web.Request) -> web.StreamResponse:
    upstream = upstream_for(request.path)
    target = f"{upstream}{request.rel_url}"
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length", "connection", "upgrade"}
    }

    async with ClientSession() as session:
        async with session.request(
            request.method,
            target,
            headers=headers,
            data=await request.read(),
            allow_redirects=False,
        ) as response:
            body = await response.read()
            proxy_response = web.Response(status=response.status, body=body)
            for key, value in response.headers.items():
                if key.lower() not in {
                    "content-encoding",
                    "content-length",
                    "connection",
                    "transfer-encoding",
                }:
                    proxy_response.headers[key] = value
            return proxy_response


async def proxy_websocket(request: web.Request) -> web.WebSocketResponse:
    upstream = upstream_for(request.path)
    target = f"{upstream.replace('http', 'ws', 1)}{request.rel_url}"
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower()
        not in {
            "host",
            "connection",
            "upgrade",
            "sec-websocket-key",
            "sec-websocket-version",
            "sec-websocket-extensions",
        }
    }
    client_ws = web.WebSocketResponse()
    await client_ws.prepare(request)

    async with ClientSession() as session:
        async with session.ws_connect(target, headers=headers, max_msg_size=0) as upstream_ws:

            async def browser_to_upstream():
                try:
                    async for msg in client_ws:
                        if msg.type == WSMsgType.TEXT:
                            await upstream_ws.send_str(msg.data)
                        elif msg.type == WSMsgType.BINARY:
                            await upstream_ws.send_bytes(msg.data)
                        elif msg.type == WSMsgType.CLOSE:
                            await upstream_ws.close()
                finally:
                    if not upstream_ws.closed:
                        await upstream_ws.close()

            async def upstream_to_browser():
                try:
                    async for msg in upstream_ws:
                        if msg.type == WSMsgType.TEXT:
                            await client_ws.send_str(msg.data)
                        elif msg.type == WSMsgType.BINARY:
                            await client_ws.send_bytes(msg.data)
                        elif msg.type == WSMsgType.CLOSE:
                            await client_ws.close()
                finally:
                    if not client_ws.closed:
                        await client_ws.close()

            done, pending = await asyncio.wait(
                [asyncio.create_task(browser_to_upstream()), asyncio.create_task(upstream_to_browser())],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*done, *pending, return_exceptions=True)

    return client_ws


async def handler(request: web.Request) -> web.StreamResponse:
    if request.headers.get("upgrade", "").lower() == "websocket":
        return await proxy_websocket(request)
    return await proxy_http(request)


app = web.Application()
app.router.add_route("*", "/{path_info:.*}", handler)


if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
