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
let startOffset = 0;
while (isWeekend(startOffset)) startOffset++;
const dayOffset = ref<number>(startOffset);
// 처음 보여준 날(오늘, 주말이면 다음 월요일)이 아닌 날을 보고 있으면 돌아가기 버튼을 띄웁니다.
const isAwayFromStart = computed(() => dayOffset.value !== startOffset);
const returnLabel = startOffset === 0 ? "오늘로 돌아가기" : "다음 급식일로 돌아가기";

// 날짜를 넘긴 방향. 화면이 넘어가는 애니메이션 방향에 씁니다. (1: 다음 날, -1: 이전 날)
const slideDirection = ref<1 | -1>(1);

const nextWeekday = (offset: number, direction: 1 | -1) => {
    let next = offset + direction;
    while (isWeekend(next)) next += direction;
    return next;
};
const moveDay = (direction: 1 | -1) => {
    slideDirection.value = direction;
    dayOffset.value = nextWeekday(dayOffset.value, direction);
};
const returnToStart = () => {
    slideDirection.value = dayOffset.value > startOffset ? -1 : 1;
    dayOffset.value = startOffset;
};

const queryAt = (offset: number) => dateAt(offset).toISOString().slice(0, 10);
const targetDate = computed(() => dateAt(dayOffset.value));
const dateQuery = computed(() => queryAt(dayOffset.value));
const dateLabel = computed(() => {
    const d = targetDate.value;
    return `${d.getUTCMonth() + 1}월 ${d.getUTCDate()}일 (${WEEKDAYS[d.getUTCDay()]})`;
});
const RELATIVE_LABELS: Record<number, string> = { [-1]: "어제", 0: "오늘", 1: "내일" };
const relativeLabel = computed(() => RELATIVE_LABELS[dayOffset.value] ?? (dayOffset.value > 0 ? `${dayOffset.value}일 후` : `${dayOffset.value * -1}일 전`));

// 날짜별로 받아 온 급식을 기억해 두고, 앞뒤 수업일도 미리 받아 둡니다.
// 날짜를 넘길 때 이미 받아 둔 급식을 바로 보여줘 로딩 화면이 깜박이지 않게 합니다.
const mealCache = shallowReactive(new Map<string, MealInfo[]>());
const mealErrors = shallowReactive(new Map<string, unknown>());
const pendingRequests = new Map<string, Promise<void>>();

type MealResult = { meals: MealInfo[] } | { error: unknown };
const requestMeals = async (date: string): Promise<MealResult> => {
    const req = await $API.getMealsMealGet({ query: { date } });
    return req.error ? { error: req.error } : { meals: req.data.data ?? [] };
};

const loadMeals = (date: string): Promise<void> => {
    if (mealCache.has(date)) return Promise.resolve();
    let request = pendingRequests.get(date);
    if (!request) {
        mealErrors.delete(date);
        request = requestMeals(date)
            .then((result) => {
                if ("meals" in result) mealCache.set(date, result.meals);
                else mealErrors.set(date, result.error);
            })
            .finally(() => pendingRequests.delete(date));
        pendingRequests.set(date, request);
    }
    return request;
};

const showError = (date: string) => {
    toast.add({ title: "급식을 불러오지 못했어요.", description: karaokeErrorMessage(mealErrors.get(date)), color: "error" });
};

// 처음 보여줄 날짜는 서버 렌더링에서 받아 옵니다.
const startQuery = queryAt(startOffset);
const { data: startMeals } = await useAsyncData(`meal.day.${startQuery}`, () => requestMeals(startQuery));
if (startMeals.value && "meals" in startMeals.value) mealCache.set(startQuery, startMeals.value.meals);

const showCurrent = async (date: string) => {
    await loadMeals(date);
    if (date !== dateQuery.value) return;
    if (mealErrors.has(date)) showError(date);
    // 다음에 넘길 앞뒤 수업일을 미리 받아 둡니다. 실패해도 알리지 않고, 그 날짜를 볼 때 다시 요청합니다.
    for (const direction of [1, -1] as const) {
        void loadMeals(queryAt(nextWeekday(dayOffset.value, direction)));
    }
};
onMounted(() => watch(dateQuery, showCurrent, { immediate: true }));

const retry = () => {
    mealErrors.delete(dateQuery.value);
    void showCurrent(dateQuery.value);
};

const meals = computed(() => mealCache.get(dateQuery.value));
const mealState = computed(() => {
    if (meals.value) return meals.value.length ? "meals" : "empty";
    return mealErrors.has(dateQuery.value) ? "error" : "loading";
});
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
        <Transition :name="slideDirection === 1 ? 'meal-next' : 'meal-prev'" mode="out-in">
            <div :key="dateQuery" class="text-center">
                <p class="text-p0 font-semibold">{{ dateLabel }}</p>
                <p class="text-ui-p2 light:text-black/50 dark:text-white/50 mt-0.5">{{ relativeLabel }}</p>
            </div>
        </Transition>
        <UButton @click="moveDay(1)" color="neutral" variant="ghost" icon="i-ph-caret-right-bold" aria-label="다음 날" class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented" size="lg" />
    </div>

    <hr class="border-default my-5" />

    <!-- 내용 높이가 바뀌어도 화면이 위아래로 튀지 않게 최소 높이를 둡니다. -->
    <div class="min-h-[60dvh] overflow-x-clip">
        <Transition :name="slideDirection === 1 ? 'meal-next' : 'meal-prev'" mode="out-in">
            <div :key="dateQuery">
                <Transition name="meal-fade" mode="out-in">
                    <div v-if="mealState === 'loading'" key="loading" class="space-y-10">
                        <USkeleton v-for="i in 3" :key="i" class="h-52 rounded-2xl" />
                    </div>
                    <div v-else-if="mealState === 'meals'" key="meals" class="space-y-10">
                        <MealCard v-for="item in meals" :key="item.type" :item="item" />
                    </div>
                    <div v-else-if="mealState === 'error'" key="error" class="text-center py-16 light:text-black/50 dark:text-white/50">
                        <UIcon name="i-ph-warning-circle" class="text-h6" />
                        <p class="text-p1 mt-2">급식을 불러오지 못했어요</p>
                        <UButton @click="retry" color="neutral" variant="soft" class="mt-4 rounded-xl">다시 시도</UButton>
                    </div>
                    <div v-else key="empty" class="text-center py-16 light:text-black/50 dark:text-white/50">
                        <UIcon name="i-ph-bowl-food" class="text-h6" />
                        <p class="text-p1 mt-2">급식 정보가 없어요</p>
                    </div>
                </Transition>
            </div>
        </Transition>
    </div>

    <!-- 플로팅 버튼이 마지막 급식 카드를 가리지 않도록 공간을 둡니다. -->
    <div v-if="isAwayFromStart" class="h-20" />

    <Transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 translate-y-4"
        leave-active-class="transition duration-150 ease-in"
        leave-to-class="opacity-0 translate-y-4"
    >
        <div v-if="isAwayFromStart" class="fixed inset-x-0 bottom-[calc(env(safe-area-inset-bottom)+1.25rem)] flex justify-center pointer-events-none">
            <UButton @click="returnToStart" icon="i-ph-arrow-counter-clockwise-bold" size="xl" class="pointer-events-auto rounded-full px-5 py-3 shadow-lg transition-all active:scale-95">
                <p class="text-p1">{{ returnLabel }}</p>
            </UButton>
        </div>
    </Transition>
</template>

<style scoped>
.meal-next-enter-active,
.meal-prev-enter-active {
    transition: opacity 0.2s ease-out, transform 0.2s ease-out;
}
.meal-next-leave-active,
.meal-prev-leave-active {
    transition: opacity 0.12s ease-in, transform 0.12s ease-in;
}
.meal-next-enter-from,
.meal-prev-leave-to {
    opacity: 0;
    transform: translateX(24px);
}
.meal-next-leave-to,
.meal-prev-enter-from {
    opacity: 0;
    transform: translateX(-24px);
}

.meal-fade-enter-active {
    transition: opacity 0.15s ease-out;
}
.meal-fade-leave-active {
    transition: opacity 0.1s ease-in;
}
.meal-fade-enter-from,
.meal-fade-leave-to {
    opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
    .meal-next-enter-active,
    .meal-next-leave-active,
    .meal-prev-enter-active,
    .meal-prev-leave-active {
        transition: opacity 0.1s linear;
        transform: none;
    }
}
</style>
