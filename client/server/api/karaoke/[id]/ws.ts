import { WebSocket as UpstreamWebSocket } from "ws";

// Nitro의 routeRules proxy(h3 proxyRequest)는 일반 HTTP 요청만 중계할 뿐 WebSocket Upgrade를
// 지원하지 않는다. 그래서 노래방 실시간 경매 소켓은 이 라우트에서 직접 백엔드로 릴레이한다.
// 인증은 별도로 검사하지 않고 브라우저가 보낸 세션 쿠키를 그대로 백엔드에 전달해,
// 백엔드의 `LoginDep`/`VIEW_KARAOKE` 검사가 그대로 적용되도록 한다.
export default defineWebSocketHandler({
    open(peer) {
        const config = useRuntimeConfig();
        const pathname = new URL(peer.request.url, "http://internal").pathname;
        const karaokeId = pathname.match(/\/karaoke\/(\d+)\/ws$/)?.[1];

        if (!karaokeId) {
            peer.close(1008, "Invalid path");
            return;
        }

        const upstreamUrl = `${config.apiOrigin.replace(/^http/, "ws")}/karaoke/${karaokeId}/ws`;
        const upstream = new UpstreamWebSocket(upstreamUrl, {
            headers: { cookie: peer.request.headers.get("cookie") ?? "" },
        });

        peer.context.upstream = upstream;

        upstream.on("message", (data) => peer.send(data.toString()));
        upstream.on("close", (code, reason) => peer.close(code, reason.toString()));
        upstream.on("error", () => peer.close(1011, "Upstream connection failed"));
    },
    message(peer, message) {
        const upstream = peer.context.upstream as UpstreamWebSocket | undefined;
        if (upstream?.readyState === UpstreamWebSocket.OPEN) {
            upstream.send(message.text());
        }
    },
    close(peer) {
        (peer.context.upstream as UpstreamWebSocket | undefined)?.close();
    },
});
