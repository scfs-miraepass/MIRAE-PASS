<script setup lang="ts">
const { add: addToast } = useToast()
const { userAgent } = useDevice()
const nuxtApp = useNuxtApp()
const _load = ref<boolean>(true)
const showLoading = ref<boolean>(false)
const isTransition = useState('isTransition', () => true)
const [scope, animate] = useAnimate()
let showLoadingTimeout: ReturnType<typeof setTimeout> | undefined;
const isKakao = computed<boolean>(() =>  /kakaotalk/i.test(userAgent || ''))

const config = useRuntimeConfig()

useHead({
    script: [
        {
            src: `${config.public.umamiServer}/script.js`,
            'data-website-id': config.public.umamiId
        }
    ]
})

nuxtApp.hook('page:loading:end', () => {
    isTransition.value = false
})

watch(isTransition, (value) => {
    animate(
        scope.value,
        { opacity: value? 0:1 },
        {
            duration: 0.3,
            ease: [0, 0.71, 0.2, 1.01],
        }
    )
    if (value) {
        showLoadingTimeout = setTimeout(() => showLoading.value = true, 500)
    } else {
        showLoading.value = false
        clearTimeout(showLoadingTimeout)
    }
})

onMounted(() => {
    setTimeout(() => _load.value = false, 500)
    if (nuxtApp.$pwa?.offlineReady) {
        addToast({
            description: '오프라인 상태입니다.',
            color: "warning"
        })
    }
})



const ANDROID_GUIDE = [
    { id: '1', text: '브라우저 메뉴를 엽니다.' },
    { id: '2', text: '"홈 화면에 추가" 메뉴를 선택합니다.' },
    { id: '3', text: '설치 버튼을 클릭합니다.' },
    { id: '4', text: '설치 버튼을 클릭합니다.' },
]

const IOS_GUIDE = [
    { id: '1', text: '브라우저 설정 메뉴를 엽니다.' },
    { id: '2', text: '"공유" 메뉴를 선택합니다.' },
    { id: '3', text: '"더 보기"를 선택합니다.' },
    { id: '4', text: '하단에 있는 "홈 화면에 추가"를 선택합니다.' },
    { id: '5', text: '"웹 앱으로 열기"를 활성화 하고. "추가"를 클릭합니다.' },
]

const isDev = import.meta.dev
const isPwaReady = computed(() => !nuxtApp.$pwa?.isPWAInstalled && !_load.value)
const isMacIpad = computed<boolean>(() => {
    if (import.meta.client) {
        return /Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1
    }
    return false
})
</script>

<template>
    <NuxtPwaManifest />
    <UApp>
        <div>
            <div
                class="w-screen min-h-screen flex items-center justify-center"
                v-if="!$device.isMobileOrTablet && !isMacIpad && !_load && !isDev"
            >
                <p class="text-p1">모바일 전용 서비스입니다! 모바일 기기에서 접속해주세요.</p>
            </div>
            <div v-else>
                <div v-show="$pwa?.needRefresh" class="fixed top-0 left-0 light:bg-black/80 dark:bg-white/80 w-dvw h-dvh flex flex-col items-center justify-center">
                    <p class="text-p2 light:text-white dark:text-black mb-4">새로운 컨텐츠가 있어요. 아래의 버튼눌러 새로고침 해주세요.</p>
                    <UButton size="xl" @click="$pwa?.updateServiceWorker()">
                        새로고침
                    </UButton>
                </div>
                <div class="w-dvw h-dvh flex flex-col items-center justify-center pwa-only-error p-7" v-if="isPwaReady && !isDev">
                    <div class="flex flex-col items-center justify-center">
                        <p class="text-p1">미래패스 앱 설치 안내</p>

                        <template v-if="!isKakao">
                            <p class="text-p2 light:text-black/50 dark:text-white/50 mt-2">미래 패스는 앱을 설치하셔야 사용 하실 수 있습니다.</p>
                            <p class="text-p2 light:text-black/50 dark:text-white/50 mt-1">'크롬(Chrome)' 브라우저 사용을 권장드립니다.</p>

                            <div class="w-full mt-7" v-if="$pwa?.showInstallPrompt">
                                <p class="text-p2 light:text-black/50 dark:text-white/50 mt-1 text-center mb-3">아래의 버튼을 눌러 설치하세요!</p>
                                <UButton class="rounded-2xl justify-center flex py-3 w-full" @click="$pwa?.install()">
                                    <p class="text-p1">설치하기</p>
                                </UButton>
                            </div>

                            <div class="mt-10" v-else-if="$device.isAndroid">
                                <UCarousel
                                    v-slot="{ item }"
                                    arrows
                                    wheel-gestures
                                    dots
                                    :items="ANDROID_GUIDE"
                                    :ui="{ dots: 'bottom-0 mt-5 relative' }"
                                >
                                    <div class="flex flex-col items-center">
                                        <img
                                            :src="`/guide/android/${item.id}.jpg`"
                                            class="h-[60vh] rounded-2xl object-contain w-fit"
                                            loading="lazy"
                                        >
                                        <p class="mt-4 text-p2">{{ item.text }}</p>
                                    </div>
                                </UCarousel>
                            </div>
                            <div class="mt-10" v-else-if="$device.isApple">
                                <UCarousel
                                    v-slot="{ item }"
                                    arrows
                                    wheel-gestures
                                    dots
                                    :items="IOS_GUIDE"
                                    :ui="{ dots: 'bottom-0 mt-5 relative' }"
                                >
                                    <div class="flex flex-col items-center">
                                        <img
                                            :src="`/guide/ios/${item.id}.PNG`"
                                            class="h-[60vh] rounded-2xl object-contain w-fit"
                                            loading="lazy"
                                        >
                                        <p class="mt-4 text-p2">{{ item.text }}</p>
                                    </div>
                                </UCarousel>
                            </div>
                        </template>
                        <template v-else>
                            <p class="text-p2 light:text-black/50 dark:text-white/50 mt-2">카카오톡에선 미래패스 이용하실 수 없습니다.</p>
                            <p class="text-p2 light:text-black/50 dark:text-white/50 mt-1">아래의 가이드를 참고해 다른 브라우저으로 접속해주세요.</p>

                            <div class="mt-10">
                                <div class="flex flex-col items-center">
                                    <img
                                        src="/guide/kakao.jpg"
                                        class="h-[60vh] rounded-2xl object-contain w-fit"
                                        loading="lazy"
                                    >
                                    <p class="mt-4 text-p2/[1.4em] text-center">하단의 메뉴를 눌러<br />'다른 브라우저로 열기'를 눌러 접속할 수 있어요</p>
                                </div>
                            </div>
                        </template>
                    </div>
                </div>
                <NuxtLoadingIndicator color="var(--ui-primary)" errorColor="var(--ui-error)" class="ease-[cubic-bezier(0,0.71,0.2,1.01)]" :class="{ 'opacity-0!': !showLoading }" />
                <div :class="[isDev? 'block!':'pwa-only-content']" ref="scope">
                    <NuxtLayout>
                        <NuxtPage />
                    </NuxtLayout>
                </div>
            </div>
        </div>
    </UApp>
</template>