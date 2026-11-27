<script setup lang="ts">
import Section from "@/components/setting/section.vue";
import Obj from "@/components/setting/object.vue";

const session = useSession();
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

const toast = useToast()
const push = usePushNotification()
const pushBusy = ref(false)
const PUSH_LABELS = { on: '켜짐', off: '꺼짐', denied: '거부됨', unsupported: '지원 안 함' } as const

onMounted(() => push.refresh())

const handlePush = async () => {
    if (pushBusy.value) return
    pushBusy.value = true
    try {
        if (push.state.value === 'on') {
            await push.disable()
            toast.add({ title: '이 기기의 알림을 껐어요.', color: 'success' })
            return
        }
        const error = await push.enable()
        if (error) toast.add({ title: '알림을 켜지 못했어요.', description: error, color: 'error' })
        else toast.add({ title: '이제 포인트 알림과 공지 알림을 받아요.', color: 'success' })
    } finally {
        pushBusy.value = false
    }
}

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
            <Obj icon="i-ph-bell" label="알림 받기" :value="PUSH_LABELS[push.state.value]" :disabled="pushBusy" @click="handlePush" />
        </Section>
        <Section name="계정">
            <NuxtLink to="/setting/kiosk" v-slot="{ navigate }" custom>
                <Obj icon="i-ph-password" label="키오스크 비밀번호" @click="navigate" />
            </NuxtLink>
            <Obj icon="i-ph-sign-out" label="로그아웃" @click="handleLogout" />
        </Section>
        <div class="text-ui-p2 space-y-1 light:text-black/20 dark:text-white/20 text-center">
            <p class="light:text-black/50 dark:text-white/50">사용자 고유번호: {{ session!.id }}</p>
            <p>Version: {{ serverVersion }}</p>
            <p>BuildDate: KST {{ config.public.buildDate }}</p>
        </div>
    </div>
</template>