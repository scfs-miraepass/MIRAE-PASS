// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
    devtools: { enabled: false },
    compatibilityDate: "2026-05-03",

    future: {
        compatibilityVersion: 4,
    },
    typescript: {
        typeCheck: "build",
        strict: true,
    },

    vite: {
        server: {
            allowedHosts: true,
        },
    },

    modules: ["@nuxt/ui", "@vueuse/nuxt", "@nuxt/fonts"],

    routeRules: {
        "/api/**": {
            proxy:
                process.env.NODE_ENV === "production"
                    ? undefined
                    : "http://localhost:8000/**",
        },
    },

    icon: {
        localApiEndpoint: "/_icon/api",
    },

    fonts: {
        families: [{ name: "Pretendard", provider: "local" }],
    },

    app: {
        baseURL: "/admin/",
        head: {
            title: "미래패스 관리자",
            htmlAttrs: {
                lang: "ko",
            },
            link: [{ rel: "icon", href: "/favicon.ico" }],
        },
    },

    css: ["~/assets/css/main.css"],
});
