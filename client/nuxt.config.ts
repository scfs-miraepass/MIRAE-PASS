import tailwindcss from "@tailwindcss/vite";
import pkg from './package.json'

// iOS 보안상 빌드해야지 PWA가 정상 작동함 Tlqkf

// Nitro의 routeRules proxy(h3 proxyRequest)는 일반 HTTP 요청만 중계할 뿐 WebSocket Upgrade는 지원하지 않는다.
// 그래서 이 값은 routeRules(일반 API 요청)와 server/routes의 수동 WS 프록시(노래방 실시간 경매)가 함께 참조한다.
const backendOrigin = process.env.NODE_ENV === 'production' ? 'http://backend:8000' : 'http://localhost:8000';

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
    compatibilityDate: "2025-07-15",
    devtools: { enabled: true },

    future: {
        compatibilityVersion: 4,
    },
    experimental: {
        viteEnvironmentApi: true,
    },
    typescript: {
        typeCheck: 'build',
        strict: true
    },

    vite: {
        plugins: [tailwindcss()],
        server: {
            allowedHosts: true, // DEV Only
        },
        optimizeDeps: {
            include: [
                '@vue/devtools-core',
                '@vue/devtools-kit',
                'workbox-window',
                '@vueuse/core',
            ]
        }
    },

    icon: {
        localApiEndpoint: "/_icon/api"
    },

    app: {
        head: {
            title: "미래패스",
            link: [
                { rel: "apple-touch-icon", href: "/apple-touch-icon.png" },
                { rel: "icon", href: "/favicon.ico", sizes: "48x48" },
                {
                    rel: "icon",
                    href: "/favicon.svg",
                    sizes: "any",
                    type: "image/svg+xml",
                },
                // iOS Startup Images - Landscape
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 440px) and (device-height: 956px) and (-webkit-device-pixel-ratio: 3) and (orientation: landscape)', href: '/pwa/splash/iPhone_17_Pro_Max__iPhone_16_Pro_Max_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 402px) and (device-height: 874px) and (-webkit-device-pixel-ratio: 3) and (orientation: landscape)', href: '/pwa/splash/iPhone_17_Pro__iPhone_17__iPhone_16_Pro_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 430px) and (device-height: 932px) and (-webkit-device-pixel-ratio: 3) and (orientation: landscape)', href: '/pwa/splash/iPhone_16_Plus__iPhone_15_Pro_Max__iPhone_15_Plus__iPhone_14_Pro_Max_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 420px) and (device-height: 912px) and (-webkit-device-pixel-ratio: 3) and (orientation: landscape)', href: '/pwa/splash/iPhone_Air_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 393px) and (device-height: 852px) and (-webkit-device-pixel-ratio: 3) and (orientation: landscape)', href: '/pwa/splash/iPhone_16__iPhone_15_Pro__iPhone_15__iPhone_14_Pro_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 428px) and (device-height: 926px) and (-webkit-device-pixel-ratio: 3) and (orientation: landscape)', href: '/pwa/splash/iPhone_14_Plus__iPhone_13_Pro_Max__iPhone_12_Pro_Max_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 390px) and (device-height: 844px) and (-webkit-device-pixel-ratio: 3) and (orientation: landscape)', href: '/pwa/splash/iPhone_17e__iPhone_16e__iPhone_14__iPhone_13_Pro__iPhone_13__iPhone_12_Pro__iPhone_12_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 375px) and (device-height: 812px) and (-webkit-device-pixel-ratio: 3) and (orientation: landscape)', href: '/pwa/splash/iPhone_13_mini__iPhone_12_mini__iPhone_11_Pro__iPhone_XS__iPhone_X_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 414px) and (device-height: 896px) and (-webkit-device-pixel-ratio: 3) and (orientation: landscape)', href: '/pwa/splash/iPhone_11_Pro_Max__iPhone_XS_Max_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 414px) and (device-height: 896px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)', href: '/pwa/splash/iPhone_11__iPhone_XR_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 414px) and (device-height: 736px) and (-webkit-device-pixel-ratio: 3) and (orientation: landscape)', href: '/pwa/splash/iPhone_8_Plus__iPhone_7_Plus__iPhone_6s_Plus__iPhone_6_Plus_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 375px) and (device-height: 667px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)', href: '/pwa/splash/iPhone_8__iPhone_7__iPhone_6s__iPhone_6__4.7__iPhone_SE_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 320px) and (device-height: 568px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)', href: '/pwa/splash/4__iPhone_SE__iPod_touch_5th_generation_and_later_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 1032px) and (device-height: 1376px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)', href: '/pwa/splash/13__iPad_Pro_M4_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 1024px) and (device-height: 1366px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)', href: '/pwa/splash/12.9__iPad_Pro_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 834px) and (device-height: 1210px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)', href: '/pwa/splash/11__iPad_Pro_M4_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 834px) and (device-height: 1194px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)', href: '/pwa/splash/11__iPad_Pro__10.5__iPad_Pro_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 820px) and (device-height: 1180px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)', href: '/pwa/splash/10.9__iPad_Air_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 834px) and (device-height: 1112px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)', href: '/pwa/splash/10.5__iPad_Air_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 810px) and (device-height: 1080px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)', href: '/pwa/splash/10.2__iPad_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 768px) and (device-height: 1024px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)', href: '/pwa/splash/9.7__iPad_Pro__7.9__iPad_mini__9.7__iPad_Air__9.7__iPad_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 744px) and (device-height: 1133px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)', href: '/pwa/splash/8.3__iPad_Mini_landscape.png' },

                // iOS Startup Images - Portrait
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 440px) and (device-height: 956px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)', href: '/pwa/splash/iPhone_17_Pro_Max__iPhone_16_Pro_Max_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 402px) and (device-height: 874px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)', href: '/pwa/splash/iPhone_17_Pro__iPhone_17__iPhone_16_Pro_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 430px) and (device-height: 932px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)', href: '/pwa/splash/iPhone_16_Plus__iPhone_15_Pro_Max__iPhone_15_Plus__iPhone_14_Pro_Max_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 420px) and (device-height: 912px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)', href: '/pwa/splash/iPhone_Air_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 393px) and (device-height: 852px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)', href: '/pwa/splash/iPhone_16__iPhone_15_Pro__iPhone_15__iPhone_14_Pro_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 428px) and (device-height: 926px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)', href: '/pwa/splash/iPhone_14_Plus__iPhone_13_Pro_Max__iPhone_12_Pro_Max_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 390px) and (device-height: 844px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)', href: '/pwa/splash/iPhone_17e__iPhone_16e__iPhone_14__iPhone_13_Pro__iPhone_13__iPhone_12_Pro__iPhone_12_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 375px) and (device-height: 812px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)', href: '/pwa/splash/iPhone_13_mini__iPhone_12_mini__iPhone_11_Pro__iPhone_XS__iPhone_X_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 414px) and (device-height: 896px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)', href: '/pwa/splash/iPhone_11_Pro_Max__iPhone_XS_Max_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 414px) and (device-height: 896px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)', href: '/pwa/splash/iPhone_11__iPhone_XR_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 414px) and (device-height: 736px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)', href: '/pwa/splash/iPhone_8_Plus__iPhone_7_Plus__iPhone_6s_Plus__iPhone_6_Plus_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 375px) and (device-height: 667px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)', href: '/pwa/splash/iPhone_8__iPhone_7__iPhone_6s__iPhone_6__4.7__iPhone_SE_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 320px) and (device-height: 568px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)', href: '/pwa/splash/4__iPhone_SE__iPod_touch_5th_generation_and_later_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 1032px) and (device-height: 1376px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)', href: '/pwa/splash/13__iPad_Pro_M4_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 1024px) and (device-height: 1366px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)', href: '/pwa/splash/12.9__iPad_Pro_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 834px) and (device-height: 1210px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)', href: '/pwa/splash/11__iPad_Pro_M4_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 834px) and (device-height: 1194px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)', href: '/pwa/splash/11__iPad_Pro__10.5__iPad_Pro_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 820px) and (device-height: 1180px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)', href: '/pwa/splash/10.9__iPad_Air_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 834px) and (device-height: 1112px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)', href: '/pwa/splash/10.5__iPad_Air_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 810px) and (device-height: 1080px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)', href: '/pwa/splash/10.2__iPad_portrait.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 768px) and (device-height: 1024px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)', href: '/pwa/splash/9.7__iPad_Pro__7.9__iPad_mini__9.7__iPad_Air__9.7__iPad_landscape.png' },
                { rel: 'apple-touch-startup-image', media: 'screen and (device-width: 744px) and (device-height: 1133px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)', href: '/pwa/splash/8.3__iPad_Mini_portrait.png' },
            ],
            meta: [
                {
                    name: "theme-color",
                    content: "#F1F5F9",
                    media: "(prefers-color-scheme: light)",
                },
                {
                    name: "theme-color",
                    content: "#0f172b",
                    media: "(prefers-color-scheme: dark)",
                },
                {
                    name: "viewport",
                    content: "initial-scale=1.0,maximum-scale=1.0,minimum-scale=1.0,user-scalable=no",
                },
                { name: 'mobile-web-app-capable', content: 'yes' },
                { name: 'apple-mobile-web-app-status-bar-style', content: 'black-translucent' },
                { name: 'apple-mobile-web-app-title', content: '미래 패스' },
            ],
            htmlAttrs: {
                lang: 'ko',
            },
        },
    },

    css: ["~/assets/styles/main.css", "~/assets/styles/tossface.css"],

    routeRules: {
        '/api/**': {
            proxy: `${backendOrigin}/**`,
        },
        '/admin/**': {
            proxy: process.env.NODE_ENV === 'production' ? 'http://dashboard:5234/**' : 'http://localhost:5234/**',
        },
    },

    nitro: {
        experimental: {
            // /api/karaoke/{id}/ws 수동 WS 프록시(server/routes)를 등록하기 위해 필요
            websocket: true,
        },
    },

    runtimeConfig: {
        apiOrigin: backendOrigin, // NUXT_API_ORIGIN (서버 전용, WS 프록시가 참조)
        public: {
            buildDate: new Date(new Date().getTime() + 9 * 60 * 60 * 1000).toISOString().replace('T', ' ').slice(0, 16), // NUXT_PUBLIC_BUILD_DATE
            clientVersion: pkg.version, // NUXT_PUBLIC_CLIENT_VERSION
            umamiServer: '', // NUXT_PUBLIC_UMAMI_SERVER
            umamiId: '', // NUXT_PUBLIC_UMAMI_ID
        },
    },

    modules: [
        "@nuxt/fonts",
        "@nuxtjs/device",
        "motion-v/nuxt",
        "@nuxt/ui",
        "@vite-pwa/nuxt",
    ],

    fonts: {
        families: [{ name: "Pretendard", provider: "local" }],
    },
    pwa: {
        includeAssets: ["favicon.ico", "apple-touch-icon.png"],
        client: {
            installPrompt: true,
        },
        devOptions: {
            enabled: import.meta.dev,
            type: "module",
        },
        registerType: "autoUpdate",
        manifest: {
            name: "미래패스",
            short_name: "미래패스",
            lang: "ko",
            id: "/",
            icons: [
                {
                    src: "/pwa/pwa-192x192.png",
                    sizes: "192x192",
                    type: "image/png",
                    purpose: "any",
                },
                {
                    src: "/pwa/pwa-512x512.png",
                    sizes: "512x512",
                    type: "image/png",
                    purpose: "any",
                },
                {
                    src: "/pwa/pwa-maskable-192x192.png",
                    sizes: "192x192",
                    type: "image/png",
                    purpose: "maskable",
                },
                {
                    src: "/pwa/pwa-maskable-512x512.png",
                    sizes: "512x512",
                    type: "image/png",
                    purpose: "maskable",
                },
            ],
            start_url: "/",
            display: "standalone",
            background_color: "#F1F5F9",
            theme_color: "#F1F5F9",
            description: "순천미래과학고등학교의 교내전용 포인트 시스템 전용 앱",
            orientation: "portrait"
        },
        workbox: {
            navigateFallback: '/',

            // 1. 빌드 시 실제 존재하는 파일만 캐싱하도록 필터링합니다.
            globPatterns: ['**/*.{js,css,html,png,svg,ico}'],

            // 2. 서비스 워커가 업데이트되었을 때 즉시 제어권을 갖도록 합니다. (중요!)
            skipWaiting: true,
            clientsClaim: true,

            // 3. iOS Safari의 'Importing script...' 에러 방지를 위해 런타임을 인라인화합니다.
            inlineWorkboxRuntime: true,
        },
    },
});
