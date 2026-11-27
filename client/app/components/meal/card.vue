<script setup lang="ts">
import type { MealInfo, MealType } from "@miraepass/api-client";

defineProps<{
    item: MealInfo;
}>();

const MEAL_LABELS: Record<MealType, { label: string; icon: string }> = {
    breakfast: { label: "아침", icon: "i-ph-sun-horizon" },
    lunch: { label: "점심", icon: "i-ph-sun" },
    dinner: { label: "저녁", icon: "i-ph-moon" },
};
</script>

<template>
    <div class="rounded-3xl bg-elevated/60 px-6 py-5">
        <div class="flex items-center justify-between mb-3">
            <p class="text-p0 font-bold flex items-center gap-1.5">
                <UIcon :name="MEAL_LABELS[item.type].icon" />
                {{ MEAL_LABELS[item.type].label }}
            </p>
            <p v-if="item.calorie != null" class="text-ui-p2 light:text-black/50 dark:text-white/50">
                {{ item.calorie.toLocaleString("ko-KR") }} kcal
            </p>
        </div>
        <ul class="space-y-1.5">
            <li v-for="(dish, index) in item.dishes" :key="index" class="flex items-baseline justify-between gap-3">
                <span class="text-p1">{{ dish.name }}</span>
                <span v-if="dish.allergies?.length" class="text-p3 shrink-0 light:text-black/40 dark:text-white/40">
                    {{ dish.allergies.join(".") }}
                </span>
            </li>
        </ul>
    </div>
</template>
