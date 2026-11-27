<script setup lang="ts">
import type { MealInfo } from "@miraepass/api-client";

definePageMeta({
    permissions: [ UserPermission.VIEW_MEAL ],
});

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

const toast = useToast();

// 기기 시간대와 관계없이 학교 기준(KST) 오늘을 YYYY-MM-DD로 구합니다. (en-CA 형식이 YYYY-MM-DD)
const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul" }).format(new Date());

// 날짜 계산은 UTC 자정 기준 Date로 해서 시간대 영향을 받지 않게 합니다.
const dateAt = (offset: number) => {
    const d = new Date(`${today}T00:00:00Z`);
    d.setUTCDate(d.getUTCDate() + offset);
    return d;
};
// 토요일 · 일요일은 급식이 없으므로 건너뜁니다. (getUTCDay: 0 = 일, 6 = 토)
const isWeekend = (offset: number) => [0, 6].includes(dateAt(offset).getUTCDay());

// 오늘부터의 날짜 차이. 오늘이 주말이면 다음 월요일부터 보여줍니다.
const dayOffset = ref<number>(0);
while (isWeekend(dayOffset.value)) dayOffset.value++;

const moveDay = (direction: 1 | -1) => {
    let next = dayOffset.value + direction;
    while (isWeekend(next)) next += direction;
    dayOffset.value = next;
};

const targetDate = computed(() => dateAt(dayOffset.value));
const dateQuery = computed(() => targetDate.value.toISOString().slice(0, 10));
const dateLabel = computed(() => {
    const d = targetDate.value;
    return `${d.getUTCMonth() + 1}월 ${d.getUTCDate()}일 (${WEEKDAYS[d.getUTCDay()]})`;
});
const RELATIVE_LABELS: Record<number, string> = { [-1]: "어제", 0: "오늘", 1: "내일" };
const relativeLabel = computed(() => RELATIVE_LABELS[dayOffset.value] ?? (dayOffset.value > 0 ? `${dayOffset.value}일 후` : `${dayOffset.value * -1}일 전`));

const { data: meals, pending } = await useAsyncData(
    "meal.day",
    async (_nuxtApp, { signal }): Promise<MealInfo[]> => {
        const req = await $API.getMealsMealGet({ query: { date: dateQuery.value }, signal });
        if (req.error) {
            if (!signal.aborted) {
                toast.add({ title: "급식을 불러오지 못했어요.", description: karaokeErrorMessage(req.error), color: "error" });
            }
            return [];
        }
        return req.data.data;
    },
    { watch: [dateQuery], default: () => [] },
);
</script>

<template>
    <div class="flex items-center mb-4">
        <NuxtLink to="/" v-slot="{ navigate }" custom>
            <UButton @click="navigate()" color="neutral" variant="ghost" icon="i-ph-caret-left-bold" class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented" size="xl" />
        </NuxtLink>
        <p class="text-2xl font-bold text-gray-900 dark:text-white ml-1">급식</p>
    </div>

    <div class="flex items-center justify-between">
        <UButton @click="moveDay(-1)" color="neutral" variant="ghost" icon="i-ph-caret-left-bold" aria-label="이전 날" class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented" size="lg" />
        <div class="text-center">
            <p class="text-p0 font-semibold">{{ dateLabel }}</p>
            <p class="text-ui-p2 light:text-black/50 dark:text-white/50 mt-0.5">{{ relativeLabel }}</p>
        </div>
        <UButton @click="moveDay(1)" color="neutral" variant="ghost" icon="i-ph-caret-right-bold" aria-label="다음 날" class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented" size="lg" />
    </div>

    <hr class="border-default my-5" />

    <div v-if="pending" class="space-y-5">
        <USkeleton v-for="i in 3" :key="i" class="h-40 rounded-2xl" />
    </div>
    <div v-else-if="meals.length" class="space-y-10">
        <MealCard v-for="item in meals" :key="item.type" :item="item" />
    </div>
    <div v-else class="text-center py-16 light:text-black/50 dark:text-white/50">
        <UIcon name="i-ph-bowl-food" class="text-h6" />
        <p class="text-p1 mt-2">급식 정보가 없어요</p>
    </div>
</template>
