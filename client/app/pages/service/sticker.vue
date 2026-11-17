<script setup lang="ts">
import { Motion } from "motion-v";
import type { User, StickerBalance, StickerBulkFailure, StickerBulkGranted } from "@miraepass/api-client";

definePageMeta({
    middleware: [
        (to, from) => {
            const users = useState<User[] | undefined>(
                "system.user-select.users",
            );
            if (!users.value || users.value.length <= 0) {
                return navigateTo("/", { replace: true });
            }
        },
    ],
    permissions: [ UserPermission.GIVE_STICKER ],
});

const targets = useState<User[]>("system.user-select.users");
const toast = useToast();

// 한 명이면 보유 수를 보여주는 단건 지급, 여러 명이면 일괄 지급
const isSingle = computed(() => targets.value.length === 1);
const firstTarget = computed(() => targets.value[0]!);
const targetLabel = computed(() => (firstTarget.value.type === "teacher" ? "선생님" : "학생"));

const amount = ref<number>(1);
const memoValue = ref<string>("");
const isLoading = ref<boolean>(false);
const isComplete = ref<boolean>(false);
const grantedAmount = ref<number>(0);
const grantedCount = ref<number>(0);
const failed = ref<StickerBulkFailure[]>([]);
// 이번 주 남은 한도 때문에 요청보다 적게 받은 사람
const partial = ref<StickerBulkGranted[]>([]);

const nameOf = (userId: number) => targets.value.find((u) => u.id === userId)?.name ?? String(userId);

const { data: balance, refresh: refreshBalance } = await useAsyncData(
    `sticker.user_balance.${firstTarget.value.id}`,
    async (_nuxtApp, { signal }): Promise<StickerBalance | null> => {
        if (!isSingle.value) return null;
        const req = await $API.getUserStickerBalance({
            path: { user_id: firstTarget.value.id! },
            signal,
        });
        if (req.error) return null;
        return req.data.data;
    },
);

const maxCount = computed(() => balance.value?.max ?? 3);
const heldCount = computed(() => balance.value?.count ?? 0);
const weekCount = computed(() => balance.value?.week_count ?? 0);
// 한도는 보유 수가 아니라 이번 주에 받은 수 기준. 여러 명일 때는 서버가 유저마다 판단하므로 전부 선택 가능
const remaining = computed(() => (isSingle.value ? Math.max(0, maxCount.value - weekCount.value) : maxCount.value));
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

// 실패한 유저 ID를 이름으로 바꿔 보여주기 위한 목록
const failedItems = computed(() => failed.value.map((item) => ({ ...item, name: nameOf(item.user_id) })));
const partialItems = computed(() => partial.value.map((item) => ({ ...item, name: nameOf(item.user_id) })));

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

    const memo = memoValue.value.trim().length > 0 ? memoValue.value.trim() : undefined;

    if (isSingle.value) {
        const req = await $API.grantSticker({
            body: { user_id: firstTarget.value.id!, amount: amount.value, memo },
        });

        if (req.error) {
            toast.add({ title: "지급하지 못했어요.", description: stickerErrorMessage(req.error), color: "error" });
            // 다른 곳에서 보유 수가 바뀌었을 수 있으므로 최신 보유 수로 갱신
            await refreshBalance();
            isLoading.value = false;
            return;
        }

        balance.value = req.data.data;
        grantedCount.value = 1;
        failed.value = [];
        partial.value = [];
    } else {
        const req = await $API.grantStickers({
            body: { user_ids: targets.value.map((u) => u.id!), amount: amount.value, memo },
        });

        if (req.error) {
            toast.add({ title: "지급하지 못했어요.", description: stickerErrorMessage(req.error), color: "error" });
            isLoading.value = false;
            return;
        }

        // 전원 실패면 완료 화면 대신 토스트로 알리고 폼에 머무름
        if (req.data.data.succeeded.length <= 0) {
            toast.add({
                title: "아무에게도 지급하지 못했어요.",
                description: req.data.data.failed.map((f) => f.reason)[0],
                color: "error",
            });
            isLoading.value = false;
            return;
        }

        grantedCount.value = req.data.data.succeeded.length;
        failed.value = req.data.data.failed;
        partial.value = req.data.data.succeeded.filter((item) => item.granted < amount.value);
    }

    grantedAmount.value = amount.value;
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
                            >{{ firstTarget.name }}</span
                        >
                        <template v-if="isSingle"> {{ targetLabel }}에게</template>
                        <template v-else> 외 {{ targets.length - 1 }}명에게</template>
                    </p>
                    <p
                        class="text-p0 light:text-black/70 dark:text-white/70 font-normal"
                    >
                        스티커를 몇 개 줄까요?
                    </p>
                    <p
                        v-if="isSingle"
                        class="text-ui-p2 mt-3 px-3 py-1.5 rounded-xl dark:bg-muted light:text-black/45 dark:text-white/40 w-fit flex items-center gap-1"
                    >
                        <UIcon name="i-ph-heart" />
                        <template v-if="remaining > 0">{{ heldCount }}개 보유 · 이번 주 {{ weekCount }}개 받음 · {{ remaining }}개 더 받을 수 있어요</template>
                        <template v-else>{{ heldCount }}개 보유 · 이번 주 한도({{ maxCount }}개)를 모두 받았어요</template>
                    </p>
                    <p
                        v-else
                        class="text-ui-p2 mt-3 px-3 py-1.5 rounded-xl dark:bg-muted light:text-black/45 dark:text-white/40 w-fit flex items-center gap-1"
                    >
                        <UIcon name="i-ph-users" />
                        한 명마다 같은 개수를 지급해요
                    </p>
                </div>

                <!-- 현재 보유 하트 (단건: 이번 주 받은 수 기준) -->
                <div class="flex items-center justify-center gap-3 mt-16">
                    <span
                        v-for="i in maxCount"
                        :key="i"
                        class="tossface text-5xl transition-all duration-300"
                        :class="{
                            'opacity-30 grayscale': i > weekCount && i > weekCount + amount,
                            'scale-110': i > weekCount && i <= weekCount + amount && remaining > 0,
                        }"
                    >
                        {{ i <= weekCount ? "💗" : (i <= weekCount + amount && remaining > 0 ? "💗" : "🤍") }}
                    </span>
                </div>

                <!-- 수량 선택 -->
                <div class="flex items-center justify-center gap-3 mt-10">
                    <UButton
                        v-for="n in maxCount"
                        :key="n"
                        :variant="amount === n ? 'solid' : 'subtle'"
                        :disabled="n > remaining || isLoading"
                        class="rounded-xl w-16 h-14 justify-center text-ui-p1"
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
                    :ui="{ base: 'rounded-xl' }"
                    :disabled="isLoading || remaining <= 0"
                />
            </div>

            <p
                class="text-ui-p2 mb-5 flex items-center justify-center light:text-black/50 dark:text-white/50"
            >
                <UIcon name="i-ph-info" class="mr-1" />
                스티커는 한 주에 최대 {{ maxCount }}개까지 받을 수 있어요.
            </p>
            <div class="space-y-3 mb-3">
                <UButton
                    class="rounded-2xl justify-center flex py-4.5 transition-opacity w-full"
                    @click="giveSticker"
                    :disabled="isLoading || remaining <= 0"
                    :loading="isLoading"
                >
                    <p class="text-p0">
                        {{ !isLoading ? (isSingle ? `${amount}개 지급하기` : `${targets.length}명에게 ${amount}개씩 지급하기`) : "처리중.." }}
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
                        <template v-if="isSingle">{{ firstTarget.name }} {{ targetLabel }}에게 스티커 {{ grantedAmount }}개!</template>
                        <template v-else>{{ grantedCount }}명에게 스티커 {{ partialItems.length > 0 ? `최대 ${grantedAmount}개` : `${grantedAmount}개씩` }}!</template>
                    </p>
                    <p
                        v-if="isSingle"
                        class="text-ui-p1 mt-2 light:text-black/50 dark:text-white/50 animate-fade-up-blur opacity-0 flex items-center gap-1"
                        :style="{ animationDelay: `${0.15 * grantedAmount + 0.4}s` }"
                    >
                        이제 <UIcon name="i-ph-heart" /> {{ afterCount }}개예요.
                    </p>
                    <!-- 일괄 지급에서 적게 받았거나 지급하지 못한 사람 -->
                    <div
                        v-else-if="partialItems.length > 0 || failedItems.length > 0"
                        class="mt-4 px-5 text-center animate-fade-up-blur opacity-0 space-y-3"
                        :style="{ animationDelay: `${0.15 * grantedAmount + 0.4}s` }"
                    >
                        <div v-if="partialItems.length > 0">
                            <p class="text-ui-p1 light:text-black/50 dark:text-white/50">
                                {{ partialItems.length }}명은 이번 주 남은 한도만큼만 받았어요
                            </p>
                            <p
                                v-for="item in partialItems"
                                :key="item.user_id"
                                class="text-ui-p2 mt-1 light:text-black/40 dark:text-white/40"
                            >
                                {{ item.name }} · {{ item.granted }}개
                            </p>
                        </div>
                        <div v-if="failedItems.length > 0">
                            <p class="text-ui-p1 light:text-black/50 dark:text-white/50">
                                {{ failedItems.length }}명은 지급하지 못했어요
                            </p>
                            <p
                                v-for="item in failedItems"
                                :key="item.user_id"
                                class="text-ui-p2 mt-1 light:text-black/40 dark:text-white/40"
                            >
                                {{ item.name }} · {{ item.reason }}
                            </p>
                        </div>
                    </div>
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
