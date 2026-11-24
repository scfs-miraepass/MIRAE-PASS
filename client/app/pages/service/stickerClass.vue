<script setup lang="ts">
import { Motion } from "motion-v";

definePageMeta({
    middleware: [
        () => {
            // 학급 지급은 서버가 서비스 계정만 허용하므로 다른 유형은 홈으로 보냅니다.
            const session = useSession();
            if (session.value?.type !== "service") {
                return navigateTo("/", { replace: true });
            }
        },
    ],
    permissions: [ UserPermission.GIVE_STICKER ],
});

// 한 번에 지급할 수 있는 최대 수. 서버 STICKER_MAX와 같은 값이며, 다른 지급 화면처럼 기본값 3을 사용합니다.
const MAX_AMOUNT = 3;

const toast = useToast();

const grade = ref<number | undefined>();
const number = ref<number | undefined>();
const amount = ref<number>(1);
const memoValue = ref<string>("");
const isLoading = ref<boolean>(false);
const isComplete = ref<boolean>(false);
const givenAmount = ref<number>(0);
// 현재 집계 기간에 이 학급에 지급한 누적 수 (서버 응답)
const givenTotal = ref<number>(0);

const classSelected = computed(() => grade.value != null && number.value != null);
const canSubmit = computed(() => classSelected.value && !isLoading.value);

// 완료 화면 배경 파티클 위치 (한 번만 계산)
const particles = Array.from({ length: 10 }, (_, i) => ({
    id: i,
    left: `${8 + Math.random() * 84}%`,
    top: `${15 + Math.random() * 55}%`,
    delay: 0.2 + Math.random() * 0.6,
    size: 14 + Math.round(Math.random() * 14),
}));

const triggerVibration = (pattern: number | number[]) => {
    if (typeof window !== "undefined" && window.navigator.vibrate) {
        window.navigator.vibrate(pattern);
    }
};

const giveToClass = async () => {
    if (!canSubmit.value) return;
    isLoading.value = true;

    const memo = memoValue.value.trim().length > 0 ? memoValue.value.trim() : undefined;
    const req = await $API.grantStickerToClass({
        body: {
            grade: grade.value!,
            number: number.value!,
            amount: amount.value,
            memo,
        },
    });

    if (req.error) {
        toast.add({ title: "지급하지 못했어요.", description: stickerErrorMessage(req.error), color: "error" });
        isLoading.value = false;
        return;
    }

    givenAmount.value = req.data.data.granted;
    givenTotal.value = req.data.data.given_count;
    triggerVibration([10, 50, 10]);
    isComplete.value = true;
    isLoading.value = false;
};

// 완료 화면에서 다른 학급에도 이어서 지급할 때 폼을 초기화합니다. (학년은 유지)
const giveAnother = () => {
    number.value = undefined;
    amount.value = 1;
    memoValue.value = "";
    isComplete.value = false;
};
</script>

<template>
    <div class="flex-1 overflow-hidden flex flex-col relative">
        <!-- 선택 폼 -->
        <div
            class="flex-1 flex flex-col transition"
            :class="{
                'pointer-events-none opacity-0 -translate-x-4': isComplete,
            }"
        >
            <div class="flex items-center mb-4">
                <NuxtLink to="/system/userSelect?a=give-sticker" v-slot="{ navigate }" custom>
                    <UButton @click="navigate()" color="neutral" variant="ghost" icon="i-ph-caret-left-bold" class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented" size="xl" />
                </NuxtLink>
                <p class="text-2xl font-bold text-gray-900 dark:text-white ml-1">학급에 스티커 주기</p>
            </div>

            <div class="flex-1 flex flex-col">
                <p class="text-ui-p2 light:text-black/50 dark:text-white/50">
                    학급을 골라 스티커를 바로 지급해요
                </p>

                <!-- 학년 · 반 -->
                <StickerClassPicker v-model:grade="grade" v-model:number="number" :disabled="isLoading" />

                <!-- 개수 -->
                <p class="text-ui-p1 font-semibold mt-5 mb-2">개수</p>
                <div class="flex items-center gap-3">
                    <UButton
                        v-for="n in MAX_AMOUNT"
                        :key="n"
                        :variant="amount === n ? 'solid' : 'outline'"
                        :disabled="isLoading"
                        class="rounded-2xl w-16 h-12 justify-center text-ui-p1"
                        @click="amount = n; triggerVibration(10)"
                    >
                        {{ n }}개
                    </UButton>
                </div>

                <!-- 메모 -->
                <UInput
                    v-model="memoValue"
                    type="text"
                    placeholder="메모 (선택)"
                    maxlength="100"
                    icon="i-ph-note-pencil"
                    size="xl"
                    class="w-full mt-5"
                    :ui="{ base: 'rounded-xl' }"
                    :disabled="isLoading"
                />
            </div>

            <p class="text-ui-p2 my-5 flex items-center justify-center text-center light:text-black/50 dark:text-white/50">
                <UIcon name="i-ph-info" class="mr-1 shrink-0" />
                학급에 준 스티커는 학생 개인 보유 수가 아니라 학급 순위 합계에만 더해져요.
            </p>
            <div class="space-y-3 mb-3">
                <UButton
                    class="rounded-2xl justify-center flex py-4.5 transition-opacity w-full"
                    @click="giveToClass"
                    :disabled="!canSubmit"
                    :loading="isLoading"
                >
                    <p class="text-p0">
                        {{ !isLoading ? (classSelected ? `${grade}학년 ${number}반에 ${amount}개 주기` : "학급을 선택하세요") : "처리중.." }}
                    </p>
                </UButton>
            </div>
        </div>

        <!-- 완료 화면 -->
        <div
            class="pt-10 h-full w-full flex flex-col items-center justify-center absolute transition overflow-hidden"
            :class="{
                'pointer-events-none opacity-0 translate-x-4': !isComplete,
            }"
        >
            <template v-if="isComplete">
                <Motion
                    v-for="p in particles"
                    :key="p.id"
                    as="span"
                    class="tossface absolute pointer-events-none select-none"
                    :style="{ left: p.left, top: p.top, fontSize: `${p.size}px` }"
                    :initial="{ scale: 0, opacity: 0, y: 0 }"
                    :animate="{ scale: [0, 1.2, 0], opacity: [0, 1, 0], y: -80 }"
                    :transition="{ duration: 1.4, delay: p.delay, ease: 'easeOut' }"
                >
                    💗
                </Motion>

                <div class="h-full flex flex-col justify-center items-center">
                    <div class="flex items-center gap-4">
                        <Motion
                            v-for="i in givenAmount"
                            :key="i"
                            as="span"
                            class="tossface text-7xl"
                            :initial="{ scale: 0, opacity: 0, y: 40, rotate: -20 }"
                            :animate="{ scale: 1, opacity: 1, y: 0, rotate: 0 }"
                            :transition="{
                                type: 'spring',
                                stiffness: 520,
                                damping: 16,
                                delay: 0.15 * (i - 1),
                            }"
                        >
                            💗
                        </Motion>
                    </div>
                    <p
                        class="text-p0 font-bold mt-10 animate-fade-up-blur opacity-0"
                        :style="{ animationDelay: `${0.15 * givenAmount + 0.2}s` }"
                    >
                        {{ grade }}학년 {{ number }}반에 스티커 {{ givenAmount }}개!
                    </p>
                    <p
                        class="text-ui-p1 mt-2 light:text-black/50 dark:text-white/50 animate-fade-up-blur opacity-0"
                        :style="{ animationDelay: `${0.15 * givenAmount + 0.4}s` }"
                    >
                        이번 기간 이 학급에 준 스티커 <UIcon name="i-ph-heart" class="inline-block align-[-2px]" /> {{ givenTotal }}개
                    </p>
                </div>
                <div class="space-y-3 mb-3 w-full">
                    <UButton
                        variant="soft"
                        color="neutral"
                        class="rounded-2xl justify-center flex py-4.5 transition-opacity w-full"
                        @click="giveAnother"
                    >
                        <p class="text-p0">다른 학급에도 주기</p>
                    </UButton>
                    <NuxtLink to="/system/userSelect?a=give-sticker" v-slot="{ navigate }" custom>
                        <UButton
                            class="rounded-2xl justify-center flex py-4.5 transition-opacity w-full"
                            @click="navigate()"
                        >
                            <p class="text-p0">돌아가기</p>
                        </UButton>
                    </NuxtLink>
                </div>
            </template>
        </div>
    </div>
</template>
