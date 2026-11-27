/// <reference lib="webworker" />
import { clientsClaim } from "workbox-core";
import { cleanupOutdatedCaches, precacheAndRoute } from "workbox-precaching";
import { NavigationRoute, registerRoute } from "workbox-routing";
import { NetworkFirst } from "workbox-strategies";

// 미래패스 서비스 워커 (@vite-pwa/nuxt injectManifest)
// 빌드하면 /sw.js로 나오며, nuxt.config.ts의 pwa 설정으로 등록됩니다.
declare let self: ServiceWorkerGlobalScope;

const PAGE_CACHE_NAME = "miraepass-pages";
const PAGE_NETWORK_TIMEOUT_SECONDS = 3;

// 서비스 워커가 처리하지 않고 네트워크로 그대로 보내는 경로
// - /api, /admin: API·관리자 페이지는 캐시하지 않습니다.
// - /_nuxt/builds: Nuxt가 새 빌드를 감지하는 파일이라 항상 서버 값을 받아야 합니다.
const NETWORK_ONLY_PATHS = [/^\/api\//, /^\/admin(\/|$)/, /^\/_icon\//, /^\/_nuxt\/builds\//];

// 새 버전이 설치되면 기다리지 않고 바로 적용합니다. (registerType: autoUpdate)
self.skipWaiting();
clientsClaim();

// 해시가 붙은 정적 파일(/_nuxt/*.js, css)과 아이콘만 미리 받아 둡니다. 목록은 빌드할 때 채워집니다.
// @vite-pwa/nuxt가 /_nuxt/builds/*.json을 목록에 직접 추가하므로 여기서 뺍니다. (캐시되면 새 빌드 감지가 늦어짐)
// 예전 버전의 사전 캐시 항목은 새 버전이 활성화될 때 정리됩니다.
precacheAndRoute(
    self.__WB_MANIFEST.filter((entry) => !(typeof entry === "string" ? entry : entry.url).startsWith("_nuxt/builds/")),
);
cleanupOutdatedCaches();

// 페이지(HTML)는 항상 서버에서 먼저 받습니다. 배포 후에도 HTML이 가리키는 청크가 서버에 있는 최신 파일과 맞게 하기 위해서입니다.
// 네트워크가 안 될 때만 마지막으로 받은 페이지를 보여줍니다.
// (SSR 앱이라 빌드 결과에 앱 셸 HTML이 없어서, 사전 캐시된 '/'로 대신 응답하는 방식은 쓰지 않습니다.)
registerRoute(
    new NavigationRoute(
        new NetworkFirst({
            cacheName: PAGE_CACHE_NAME,
            networkTimeoutSeconds: PAGE_NETWORK_TIMEOUT_SECONDS,
        }),
        { denylist: NETWORK_ONLY_PATHS },
    ),
);

// ---- 앱 알림 (웹 푸시) ----
// 서버(app/core/service/notification.py)가 보내는 PushMessage JSON: { title, body, url }
type PushMessage = { title?: string; body?: string; url?: string };

const NOTIFICATION_ICON = "/pwa/pwa-192x192.png";

self.addEventListener("push", (event) => {
    let message: PushMessage = {};
    try {
        message = event.data?.json() ?? {};
    } catch {
        message = { body: event.data?.text() };
    }
    event.waitUntil(
        self.registration.showNotification(message.title || "미래패스", {
            body: message.body ?? "",
            icon: NOTIFICATION_ICON,
            badge: NOTIFICATION_ICON,
            data: { url: message.url || "/" },
        }),
    );
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    // 앱 안 경로만 엽니다. (다른 출처 주소면 첫 화면으로)
    const target = new URL(event.notification.data?.url ?? "/", self.location.origin);
    const url = target.origin === self.location.origin ? target.href : self.location.origin;

    event.waitUntil(
        (async () => {
            const windows = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
            const opened = windows.find((client) => new URL(client.url).origin === self.location.origin);
            if (opened) {
                await opened.focus();
                if (opened.url !== url) await opened.navigate(url).catch(() => undefined);
                return;
            }
            await self.clients.openWindow(url);
        })(),
    );
});
