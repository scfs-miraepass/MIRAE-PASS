<script setup lang="ts">
// 학년 · 반 선택 그리드. 교사의 학급 전달과 서비스 계정의 학급 지급 화면에서 함께 사용합니다.
const GRADES = [1, 2, 3];
// 1, 2학년은 6반(바이오 2 · 소프트 2 · 전기과 2), 3학년은 5반(바이오 2 · 소프트 2 · 전기과 1)
const CLASS_COUNT: Record<number, number> = { 1: 6, 2: 6, 3: 5 };

const grade = defineModel<number | undefined>("grade");
const number = defineModel<number | undefined>("number");
defineProps<{
    disabled?: boolean;
}>();

const classes = computed(() =>
    grade.value != null ? Array.from({ length: CLASS_COUNT[grade.value] ?? 0 }, (_, i) => i + 1) : [],
);
const classSelected = computed(() => grade.value != null && number.value != null);

const triggerVibration = (pattern: number | number[]) => {
    if (typeof window !== "undefined" && window.navigator.vibrate) {
        window.navigator.vibrate(pattern);
    }
};

const selectGrade = (g: number) => {
    grade.value = g;
    // 학년을 바꿔 반 수가 줄어든 경우 선택된 반 해제
    if (number.value != null && number.value > (CLASS_COUNT[g] ?? 0)) number.value = undefined;
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
        <div class="grid grid-cols-3 gap-2">
            <UButton
                v-for="g in GRADES"
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
