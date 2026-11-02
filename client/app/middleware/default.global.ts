export default defineNuxtRouteMiddleware((to, from) => {
    if (import.meta.client && !to.path.startsWith("/login")) {
        const isTransition = useState('isTransition', () => true)
        isTransition.value = true

        return new Promise((resolve) => setTimeout(resolve, 250))
    }
})
