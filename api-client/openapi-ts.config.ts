import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
    // CI는 서버를 띄우지 않고 뽑은 openapi.json 파일 경로를 OPENAPI_INPUT으로 넘깁니다.
    input: process.env.OPENAPI_INPUT ?? "http://localhost:8000/openapi.json",
    output: "src/gen",
    plugins: [
        {
            name: "@hey-api/typescript",
            enums: "javascript",
        },
        {
            name: "@hey-api/client-ofetch",
            runtimeConfigPath: "./src/client.config",
        },
        {
            name: "@hey-api/sdk",
            transformer: true,
            validator: true,
            operations: {
                containerName: "MiraepassAPI",
                strategy: "single",
            },
        },
        {
            name: "zod",
            dates: {
                offset: true
            }
        },
        "@hey-api/transformers",
        "@hey-api/schemas",
    ],
});
