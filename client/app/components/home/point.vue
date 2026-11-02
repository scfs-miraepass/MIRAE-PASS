<script setup lang="ts">
import { Motion } from "motion-v";
import { useElementSize } from '@vueuse/core'

const session = useSession()

const pointBefore = computed(() => {
    return session.value!.point!.toLocaleString()
})
const pointNow = ref<string | null>(null)
const pointChangeAnimate = ref<boolean>(false)

const pointContainer = ref(null)
const { width: pointWidth } = useElementSize(pointContainer)

watch(pointBefore, (value) => {
    if (pointNow.value == null) {
        pointNow.value = value
        return
    }

    pointChangeAnimate.value = true
    setTimeout(() => {
        pointNow.value = value
        pointChangeAnimate.value = false
    }, (pointNow.value.length * 0.075 + 0.2) * 1000)
})

onMounted(() => {
    pointNow.value = pointBefore.value
})
</script>

<template>
    <div class="light:bg-default dark:bg-muted rounded-2xl p-5">
        <div class="text-p1 flex items-center gap-x-2 font-normal">
            <LogoSymbol size="18" />
            보유중인 미래 포인트
        </div>
        <div class="mt-2 text-p0 flex items-center -mb-1">
            <Motion
                :initial="{ opacity: 0, translateX: '0' }"
                :animate="{ opacity: 1, translateX: pointChangeAnimate? '0':`${pointWidth + 4}px` }"
                :transition="{
                    duration: pointNow.length * (0.15),
                    delay: pointChangeAnimate? (pointNow.length - 1) * 0.0725:0.5,
                    ease: [0, 0.71, 0.2, 1.01],
                }"
                class="absolute mt-2.5"
                v-if="pointWidth && pointNow != null"
            >P</Motion>
            <span ref="pointContainer" class="text-h5/10 tracking-tight flex items-center overflow-y-hidden">
                <template v-for="(i, index) in pointNow" v-if="pointNow != null">
                    <Motion
                        as="span"
                        :initial="{ y: '100%' }"
                        :animate="{ y: pointChangeAnimate? '100%':'0%' }"
                        :transition="{
                            duration: 0.5,
                            delay: pointChangeAnimate? ((pointNow.length - 1) * 0.075 - index * 0.075):(index * 0.075) + 0.5,
                            ease: [0, 0.71, 0.2, 1.01],
                        }"
                    >
                        {{ i }}
                    </Motion>
                </template>
            </span>
        </div>
    </div>
</template>