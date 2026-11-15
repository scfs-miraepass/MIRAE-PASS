<script setup lang="ts">
import type { StickerClassRankingResponse } from "@miraepass/api-client";

const payload = ref<StickerClassRankingResponse[]>([]);

const { pending } = await useAsyncData(
    "sticker.ranking.class",
    async () => {
        const req = await $API.getStickerClassRanking();
        if (!req.data?.success || req.response == undefined) return;
        payload.value = req.data.data;
        return req;
    },
);

// 학년별 그룹 (1학년 → 3학년), 각 그룹 내부는 서버 정렬(반 오름차순) 유지
const grouped = computed(() => {
    const map = new Map<number, StickerClassRankingResponse[]>();
    for (const row of payload.value) {
        if (!map.has(row.grade)) map.set(row.grade, []);
        map.get(row.grade)!.push(row);
    }
    let index = 0;
    return [...map.entries()]
        .sort((a, b) => a[0] - b[0])
        .map(([grade, rows]) => ({
            grade,
            rows: rows.map((row) => ({ ...row, index: index++ })),
        }));
});

const departmentOf = (number: number) =>
    number <= 2
        ? { label: "바이오", class: "text-rose-400" }
        : number <= 4
          ? { label: "소프트", class: "text-blue-400" }
          : { label: "전기과", class: "text-yellow-400" };
</script>

<template>
    <div v-if="!pending && payload.length === 0" class="text-ui-p2 light:text-black/50 dark:text-white/50 text-center">
        아직 학급 정보가 없어요
    </div>
    <div v-for="group in grouped" :key="group.grade" class="mb-8">
        <p class="text-ui-p1 font-semibold mb-3 light:text-black/60 dark:text-white/60">
            {{ group.grade }}학년
        </p>
        <div class="space-y-4">
            <div
                v-for="row in group.rows"
                :key="`${row.grade}-${row.number}`"
                class="flex items-center justify-between animate-fade-up-blur opacity-0"
                :style="{ animationDelay: `${row.index * 60}ms` }"
            >
                <div class="flex items-center">
                    <p
                        class="aspect-square w-11 mx-2.5 text-center -mb-px font-semibold"
                        :class="
                            row.rank > 3
                                ? 'text-[22px] light:text-black/50 dark:text-white/50'
                                : 'text-[30px] tossface'
                        "
                    >
                        <template v-if="row.rank == 1">🥇</template>
                        <template v-else-if="row.rank == 2">🥈</template>
                        <template v-else-if="row.rank == 3">🥉</template>
                        <template v-else>{{ row.rank }}</template>
                    </p>
                    <div class="ml-3">
                        <div class="flex items-center mb-0.5">
                            <p class="text-p1">{{ row.grade }}학년 {{ row.number }}반</p>
                            <p class="text-ui-p2 ml-1" :class="departmentOf(row.number).class">
                                {{ departmentOf(row.number).label }}
                            </p>
                        </div>
                        <p
                            class="text-ui-p2"
                            :class="row.count > 0 ? 'light:text-black/50 dark:text-white/50' : 'light:text-black/30 dark:text-white/30'"
                        >
                            <span class="tossface">♡</span> {{ row.count }}개
                            <span v-if="row.teacher_count > 0" class="ml-1.5 light:text-black/40 dark:text-white/40">
                                선생님 +{{ row.teacher_count }}
                            </span>
                        </p>
                    </div>
                </div>
                <UBadge color="neutral" variant="subtle" class="mr-3">전체 {{ row.rank }}위</UBadge>
            </div>
        </div>
    </div>
</template>
