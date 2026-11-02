<script setup lang="ts">
import type { RankingResponse } from "@/client";

const props = defineProps<RankingResponse & { period: "total" | "weekly" }>();
const pointLabel = computed(() => props.period === "weekly" ? "이번 주 포인트" : "누적 포인트");
</script>

<template>
    <div class="flex items-center justify-between">
        <div class="flex items-center">
            <p
                class="aspect-square w-11 mx-2.5 text-center -mb-px font-semibold"
                :class="
                    rank > 3
                        ? 'text-[26px] light:text-black/50 dark:text-white/50'
                        : 'text-[35px] tossface'
                "
            >
                <template v-if="rank == 1">🥇</template>
                <template v-else-if="rank == 2">🥈</template>
                <template v-else-if="rank == 3">🥉</template>
                <template v-else>{{ rank }}</template>
            </p>
            <div class="ml-3">
                <div class="flex items-center mb-0.5">
                    <p class="text-p1">{{ name }}</p>

                    <template v-if="grade >= 1">
                        <p
                            class="text-ui-p2 text-rose-400 ml-1"
                            v-if="number <= 2"
                        >
                            {{ grade }}학년 바이오
                        </p>
                        <p
                            class="text-ui-p2 text-blue-400 ml-1"
                            v-else-if="number <= 4"
                        >
                            {{ grade }}학년 소프트
                        </p>
                        <p class="text-ui-p2 text-yellow-400 ml-1" v-else>
                            {{ grade }}학년 전기과
                        </p>
                    </template>
                </div>
                <p class="text-ui-p2 light:text-black/50 dark:text-white/50">
                    {{ pointLabel }} {{ total_point.toLocaleString() }} P
                </p>
            </div>
        </div>
    </div>
</template>

<style scoped></style>
