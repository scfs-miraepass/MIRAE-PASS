<script setup lang="ts">
import type { StickerClassItem } from "@miraepass/api-client";

// 학년 · 반 선택 그리드. 교사의 학급 전달과 서비스 계정의 학급 지급 화면에서 함께 사용합니다.
// 학급 목록은 서버에서 학생이 있는 학급(학년, 반)만 받아옵니다.
const { data: classList, pending } = await useAsyncData(
    "sticker.classes",
    async (_nuxtApp, { signal }): Promise<StickerClassItem[]> => {
        const req = await $API.getStickerClasses({ signal });
        if (req.error) return [];
        return req.data.data;
    },
    { default: () => [] },
);

// 학년별 반 목록 (서버 정렬: 학년, 반 오름차순)
const classesByGrade = computed(() => {
    const map = new Map<number, number[]>();
    for (const item of classList.value) {
        if (!map.has(item.grade)) map.set(item.grade, []);
        map.get(item.grade)!.push(item.number);
    }
    return map;
});
const grades = computed(() => [...classesByGrade.value.keys()]);

const grade = defineModel<number | undefined>("grade");
const number = defineModel<number | undefined>("number");
defineProps<{
    disabled?: boolean;
}>();

const classes = computed(() => (grade.value != null ? (classesByGrade.value.get(grade.value) ?? []) : []));
const classSelected = computed(() => grade.value != null && number.value != null);

const triggerVibration = (pattern: number | number[]) => {
    if (typeof window !== "undefined" && window.navigator.vibrate) {
        window.navigator.vibrate(pattern);
    }
};

const selectGrade = (g: number) => {
    grade.value = g;
    // 바꾼 학년에 없는 반이 선택되어 있으면 선택 해제
    if (number.value != null && !(classesByGrade.value.get(g) ?? []).includes(number.value)) number.value = undefined;
    triggerVibration(10);
};

const selectNumber = (c: number) => {
    number.value = c;
    triggerVibration(10);
};
</script>

<template>
    <div>
        <!-- 학년 -->
        <p class="text-ui-p1 font-semibold mt-6 mb-2">학년</p>
        <p
            v-if="!pending && grades.length === 0"
            class="text-ui-p2 h-12 flex items-center light:text-black/40 dark:text-white/40"
        >
            학급 정보를 불러오지 못했어요
        </p>
        <div class="grid grid-cols-3 gap-2" v-else>
            <UButton
                v-for="g in grades"
                :key="g"
                :variant="grade === g ? 'solid' : 'outline'"
                :disabled="disabled"
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
                :disabled="disabled"
                class="rounded-2xl h-12 justify-center text-ui-p1"
                @click="selectNumber(c)"
            >
                {{ c }}반
            </UButton>
        </div>
        <p class="text-ui-p2 h-12 flex items-center light:text-black/40 dark:text-white/40" v-else>먼저 학년을 선택하세요</p>
        <p class="text-ui-p2 mt-2 h-5" v-if="classSelected">
            {{ grade }}학년 {{ number }}반
            <span :class="stickerDepartment(number!).class">{{ stickerDepartment(number!).label }}</span>
        </p>
        <p class="text-ui-p2 mt-2 h-5 light:text-black/40 dark:text-white/40" v-else>학년과 반을 선택하세요</p>
    </div>
</template>
