<script setup lang="ts">
import Section from "@/components/setting/section.vue";
import Obj from "@/components/setting/object.vue";

const config = useRuntimeConfig()
const colorMode = useColorMode()
const serverVersion = useServerVersion()

const themeOptions = [
    { label: '시스템', value: 'system', icon: () => colorMode.value == 'dark' ? 'i-ph-moon-fill' : 'i-ph-sun-dim' },
    { label: '라이트', value: 'light', icon: () => 'i-ph-sun-dim' },
    { label: '다크', value: 'dark', icon: () => 'i-ph-moon-fill' }
]

const selectedTheme = computed({
    get() {
        return themeOptions.find(option => option.value === colorMode.preference) || themeOptions[0]
    },
    set(option) {
        if (!option) return
        colorMode.preference = option.value
    }
})

const handleLogout = async () => {
    await navigateTo('/logout', { replace: true })
}

const handleTheme = () => {
    const currentIndex = themeOptions.findIndex(option => option.value === colorMode.preference)
    const nextIndex = (currentIndex + 1) % themeOptions.length
    colorMode.preference = themeOptions[nextIndex]!.value
}
</script>

<template>
    <div class="flex items-center mb-4">
        <NuxtLink to="/" v-slot="{ navigate }" custom>
            <UButton @click="navigate()" color="neutral" variant="ghost" icon="i-ph-caret-left-bold" class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented" size="xl" />
        </NuxtLink>
        <p class="text-2xl font-bold text-gray-900 dark:text-white ml-1">설정</p>
    </div>

    <div class="space-y-3">
        <Section>
            <Obj :icon="selectedTheme!.icon()" label="화면 테마" :value="selectedTheme!.label" @click="handleTheme" />
        </Section>
        <Section name="계정">
            <Obj icon="i-ph-sign-out" label="로그아웃" @click="handleLogout" />
        </Section>
        <div class="text-ui-p2 space-y-1 light:text-black/10 dark:text-white/10 text-center">
            <p>ClientVersion: {{ config.public.clientVersion }}</p>
            <p>ServerVersion: {{ serverVersion }}</p>
            <p>BuildDate: KST {{ config.public.buildDate }}</p>
        </div>
    </div>
</template>