import { ofetch } from 'ofetch'

export const _fetch = ofetch.create({
    credentials: "include",
    async onRequest({options}) {
        if (import.meta.env.SSR) {
            const { origin } = useRequestURL()
            options.baseURL = `${origin}/api/`
        } else {
            options.baseURL = '/api/'
        }
    }
})
