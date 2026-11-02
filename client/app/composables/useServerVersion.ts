import { useStorage } from '@vueuse/core'

export const useServerVersion =  () => useStorage<string | null>("server.version", () => null)