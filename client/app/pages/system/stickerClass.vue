<script setup lang="ts">
import { Motion } from "motion-v";
import type { StickerBalance } from "@miraepass/api-client";

definePageMeta({
    permissions: [ UserPermission.GIVE_CLASS_STICKER ],
});

const GRADES = [1, 2, 3];
// 1, 2학년은 6반(바이오 2 · 소프트 2 · 전기과 2), 3학년은 5반(바이오 2 · 소프트 2 · 전기과 1)
const CLASS_COUNT: Record<number, number> = { 1: 6, 2: 6, 3: 5 };

const toast = useToast();

const balance = ref<StickerBalance | undefined>();
const grade = ref<number | undefined>();
const number = ref<number | undefined>();
const amount = ref<number>(1);
const isLoading = ref<boolean>(false);
const isComplete = ref<boolean>(false);
const givenAmount = ref<number>(0);

const held = computed(() => balance.value?.count ?? 0);
const maxCount = computed(() => balance.value?.max ?? 3);
// 전달 성공 시 balance가 서버 응답(전달 후 보유 수)으로 갱신되므로 그대로 사용
const afterCount = computed(() => held.value);
const classes = computed(() =>
    grade.value != null ? Array.from({ length: CLASS_COUNT[grade.value] ?? 0 }, (_, i) => i + 1) : [],
);
const classSelected = computed(() => grade.value != null && number.value != null);

const selectGrade = (g: number) => {
    grade.value = g;
    // 학년을 바꿔 반 수가 줄어든 경우 선택된 반 해제
    if (number.value != null && number.value > (CLASS_COUNT[g] ?? 0)) number.value = undefined;
    triggerVibration(10);
};
const canSubmit = computed(() => classSelected.value && held.value > 0 && amount.value <= held.value && !isLoading.value);

const departmentOf = (n: number) =>
    n <= 2
        ? { label: "바이오", class: "text-rose-400" }
        : n <= 4
          ? { label: "소프트", class: "text-blue-400" }
          : { label: "전기과", class: "text-yellow-400" };

// 완료 화면 배경 파티클 위치 (한 번만 계산)
const particles = Array.from({ length: 10 }, (_, i) => ({
    id: i,
    left: `${8 + Math.random() * 84}%`,
    top: `${15 + Math.random() * 55}%`,
    delay: 0.2 + Math.random() * 0.6,
    size: 14 + Math.round(Math.random() * 14),
}));

const loadBalance = async () => {
    const req = await $API.getMyStickerBalance();
    if (!req.error) {
        balance.value = req.data.data;
        if (held.value > 0 && amount.value > held.value) amount.value = held.value;
    }
};

if (import.meta.client) {
    await loadBalance();
}

const triggerVibration = (pattern: number | number[]) => {
    if (typeof window !== "undefined" && window.navigator.vibrate) {
        window.navigator.vibrate(pattern);
    }
};

const giveToClass = async () => {
    if (!canSubmit.value) return;
    isLoading.value = true;

    const req = await $API.giveStickerToClass({
        body: {
            grade: grade.value!,
            number: number.value!,
            amount: amount.value,
        },
    });

    if (req.error) {
        if (req.response?.status == 409) {
            toast.add({ title: "전달 실패", description: "보유한 스티커가 부족해요.", color: "error" });
            await loadBalance();
        } else if (req.response?.status == 404) {
            toast.add({ title: "전달 실패", description: "해당 학급이 없어요.", color: "error" });
        } else {
            toast.add({
                title: "전달 실패",
                description: "알 수 없는 이유로 전달에 실패했습니다. 관리자에게 문의하세요.",
                color: "error",
            });
        }
        isLoading.value = false;
        return;
    }

    givenAmount.value = amount.value;
    balance.value = req.data.data;
    triggerVibration([10, 50, 10]);
    isComplete.value = true;
    isLoading.value = false;
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
                <NuxtLink to="/system/sticker" v-slot="{ navigate }" custom>
                    <UButton @click="navigate()" color="neutral" variant="ghost" icon="i-ph-caret-left-bold" class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented" size="xl" />
                </NuxtLink>
                <p class="text-2xl font-bold text-gray-900 dark:text-white ml-1">학급에 스티커 주기</p>
            </div>

            <div class="flex-1 flex flex-col">
                <p class="text-ui-p2 light:text-black/50 dark:text-white/50">
                    내 스티커 <span class="tossface">♡</span> {{ held }}개
                    <template v-if="held <= 0"> · 전달할 스티커가 없어요</template>
                </p>

                <!-- 학년 -->
                <p class="text-ui-p1 font-semibold mt-6 mb-2">학년</p>
                <div class="grid grid-cols-3 gap-2">
                    <UButton
                        v-for="g in GRADES"
                        :key="g"
                        :variant="grade === g ? 'solid' : 'outline'"
                        class="rounded-2xl h-12 justify-center text-ui-p1"
                        @click="selectGrade(g)"
                    >
                        {{ g }}학년
                    </UButton>
                </div>

                <!-- 반 -->
                <p class="text-ui-p1 font-semibold mt-5 mb-2">반</p>
                <div class="grid grid-cols-6 gap-2" v-if="grade != null">
                    <UButton
                        v-for="c in classes"
                        :key="c"
                        :variant="number === c ? 'solid' : 'outline'"
                        class="rounded-2xl h-12 justify-center text-ui-p1"
                        @click="number = c; triggerVibration(10)"
                    >
                        {{ c }}반
                    </UButton>
                </div>
                <p class="text-ui-p2 h-12 flex items-center light:text-black/40 dark:text-white/40" v-else>먼저 학년을 선택하세요</p>
                <p class="text-ui-p2 mt-2 h-5" v-if="classSelected">
                    {{ grade }}학년 {{ number }}반
                    <span :class="departmentOf(number!).class">{{ departmentOf(number!).label }}</span>
                </p>
                <p class="text-ui-p2 mt-2 h-5 light:text-black/40 dark:text-white/40" v-else>학년과 반을 선택하세요</p>

                <!-- 개수 -->
                <p class="text-ui-p1 font-semibold mt-5 mb-2">개수</p>
                <div class="flex items-center gap-3">
                    <UButton
                        v-for="n in maxCount"
                        :key="n"
                        :variant="amount === n ? 'solid' : 'outline'"
                        :disabled="n > held || isLoading"
                        class="rounded-2xl w-16 h-12 justify-center text-ui-p1"
                        @click="amount = n; triggerVibration(10)"
                    >
                        {{ n }}개
                    </UButton>
                </div>
            </div>

            <p class="text-ui-p2 my-5 flex items-center justify-center light:text-black/50 dark:text-white/50">
                <UIcon name="i-ph-info" class="mr-1" />
                전달한 스티커는 학급 순위 합계에 더해져요.
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
                        남은 내 스티커 <span class="tossface">♡</span> {{ afterCount }}개
                    </p>
                </div>
                <NuxtLink to="/system/sticker" v-slot="{ navigate }" custom>
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
