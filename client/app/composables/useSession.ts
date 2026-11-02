import type { User } from "@/client";
import { useStorage } from '@vueuse/core'

export const useSession = () => useStorage<User | undefined>("session.user", undefined, undefined, {
    serializer: { read: (v) => v ? JSON.parse(v) : null, write: (v) => JSON.stringify(v) }
})