<script setup lang="ts">
import { Motion } from "motion-v";
import type { User, StickerBalance } from "@miraepass/api-client";

definePageMeta({
    middleware: [
        (to, from) => {
            const userData = useState<User | undefined>(
                "system.user-select.uesr",
            );
            if (!userData.value) {
                return navigateTo("/", { replace: true });
            }
        },
    ],
    permissions: [ UserPermission.GIVE_STICKER ],
});

const userData = useState<User>("system.user-select.uesr");
const toast = useToast();
const targetLabel = computed(() => (userData.value.type === "teacher" ? "선생님" : "학생"));

const amount = ref<number>(1);
const memoValue = ref<string>("");
const isLoading = ref<boolean>(false);
const isComplete = ref<boolean>(false);
const grantedAmount = ref<number>(0);

const { data: balance, refresh: refreshBalance } = await useAsyncData(
    `sticker.user_balance.${userData.value.id}`,
    async (_nuxtApp, { signal }): Promise<StickerBalance | null> => {
        const req = await $API.getUserStickerBalance({
            path: { user_id: userData.value.id! },
            signal,
        });
        if (req.error) return null;
        return req.data.data;
    },
);

const maxCount = computed(() => balance.value?.max ?? 3);
const heldCount = computed(() => balance.value?.count ?? 0);
const remaining = computed(() => Math.max(0, maxCount.value - heldCount.value));
// 지급 성공 시 balance가 서버 응답(지급 후 보유 수)으로 갱신되므로 그대로 사용
const afterCount = computed(() => heldCount.value);

// 남은 지급 가능 수보다 많이 선택되어 있으면 줄임
watch(
    remaining,
    (value) => {
        if (value > 0 && amount.value > value) amount.value = value;
    },
    { immediate: true },
);

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

const giveSticker = async () => {
    if (isLoading.value || remaining.value <= 0) return;
    isLoading.value = true;

    const req = await $API.grantSticker({
        body: {
            user_id: userData.value.id!,
            amount: amount.value,
            memo: memoValue.value.trim().length > 0 ? memoValue.value.trim() : undefined,
        },
    });

    if (req.error) {
        toast.add({ title: "지급하지 못했어요.", description: stickerErrorMessage(req.error), color: "error" });
        // 다른 곳에서 보유 수가 바뀌었을 수 있으므로 최신 보유 수로 갱신
        await refreshBalance();
        isLoading.value = false;
        return;
    }

    grantedAmount.value = amount.value;
    balance.value = req.data.data;
    triggerVibration([10, 50, 10]);
    isComplete.value = true;
    isLoading.value = false;
};
</script>

<template>
    <div class="flex-1 overflow-hidden flex flex-col relative">
        <!-- 지급 폼 -->
        <div
            class="flex-1 flex flex-col transition"
            :class="{
                'pointer-events-none opacity-0 -translate-x-4': isComplete,
            }"
        >
            <div class="flex-1 flex flex-col">
                <div class="mt-24">
                    <p
                        class="text-p0 light:text-black/70 dark:text-white/70 font-normal"
                    >
                        <span
                            class="font-bold light:text-black dark:text-white"
                            >{{ userData.name }}</span
                        >
                        {{ targetLabel }}에게
                    </p>
                    <p
                        class="text-p0 text-black/70 dark:text-white/70 font-normal"
                    >
                        스티커를 몇 개 줄까요?
                    </p>
                    <p
                        class="text-ui-p2 mt-3 light:text-black/50 dark:text-white/50"
                    >
                        현재 <span class="tossface">♡</span> {{ heldCount }}개 보유 ·
                        <template v-if="remaining > 0">최대 {{ remaining }}개 지급 가능</template>
                        <template v-else>이번 달 한도({{ maxCount }}개)를 모두 받았어요</template>
                    </p>
                </div>

                <!-- 현재 보유 하트 -->
                <div class="flex items-center justify-center gap-3 mt-16">
                    <span
                        v-for="i in maxCount"
                        :key="i"
                        class="tossface text-5xl transition-all duration-300"
                        :class="{
                            'opacity-30 grayscale': i > heldCount && i > heldCount + amount,
                            'scale-110': i > heldCount && i <= heldCount + amount && remaining > 0,
                        }"
                    >
                        {{ i <= heldCount ? "💗" : (i <= heldCount + amount && remaining > 0 ? "💗" : "🤍") }}
                    </span>
                </div>

                <!-- 수량 선택 -->
                <div class="flex items-center justify-center gap-3 mt-10">
                    <UButton
                        v-for="n in maxCount"
                        :key="n"
                        :variant="amount === n ? 'solid' : 'outline'"
                        :disabled="n > remaining || isLoading"
                        class="rounded-2xl w-16 h-14 justify-center text-h5"
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
                    class="w-full mt-8"
                    :ui="{ base: 'rounded-2xl' }"
                    :disabled="isLoading || remaining <= 0"
                />
            </div>

            <p
                class="text-ui-p2 mb-5 flex items-center justify-center light:text-black/50 dark:text-white/50"
            >
                <UIcon name="i-ph-info" class="mr-1" />
                스티커는 매월 1일에 초기화돼요.
            </p>
            <div class="space-y-3 mb-3">
                <UButton
                    class="rounded-2xl justify-center flex py-4.5 transition-opacity w-full"
                    @click="giveSticker"
                    :disabled="isLoading || remaining <= 0"
                    :loading="isLoading"
                >
                    <p class="text-p0">
                        {{ !isLoading ? `${amount}개 지급하기` : "처리중.." }}
                    </p>
                </UButton>
                <UButton
                    color="error"
                    variant="soft"
                    class="rounded-2xl justify-center flex py-4.5 transition-opacity w-full"
                    :disabled="isLoading"
                    @click="$router.back()"
                >
                    <p class="text-p0">취소</p>
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
                <!-- 배경 파티클 -->
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
                            v-for="i in grantedAmount"
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
                        :style="{ animationDelay: `${0.15 * grantedAmount + 0.2}s` }"
                    >
                        {{ userData.name }} {{ targetLabel }}에게 스티커 {{ grantedAmount }}개!
                    </p>
                    <p
                        class="text-ui-p1 mt-2 light:text-black/50 dark:text-white/50 animate-fade-up-blur opacity-0"
                        :style="{ animationDelay: `${0.15 * grantedAmount + 0.4}s` }"
                    >
                        이제 <span class="tossface">♡</span> {{ afterCount }}개예요.
                    </p>
                </div>
                <NuxtLink
                    to="/system/userSelect?a=give-sticker"
                    v-slot="{ navigate }"
                    custom
                >
                    <UButton
                        class="rounded-2xl justify-center flex py-4.5 transition-opacity mb-3 w-full"
                        @click="navigate()"
                    >
                        <p class="text-p0">돌아가기</p>
                    </UButton>
                </NuxtLink>
            </template>
        </div>
    </div>
</template>
