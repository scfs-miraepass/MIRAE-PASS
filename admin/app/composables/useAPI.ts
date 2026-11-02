import type { UseFetchOptions } from "nuxt/app";

export const useAPI = <T>(
    url: string | (() => string),
    options?: UseFetchOptions<T>,
) => {
    return useFetch(url, {
        ...options,
        $fetch: _fetch as typeof globalThis.$fetch,
    });
};
