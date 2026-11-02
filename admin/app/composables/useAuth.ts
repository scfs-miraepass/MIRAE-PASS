import { useStorage } from '@vueuse/core'

export const useAuth = () => {
    // useState 대신 useStorage를 사용하여 localStorage에 저장 (브라우저 종료 후에도 유지)
    const lastFetched = useStorage<number>("session.ttl", 0)
    const resetLastFetched = () => {
        lastFetched.value = null // Storage 삭제
    }

    return {
        lastFetched,
        resetLastFetched,
    }
}