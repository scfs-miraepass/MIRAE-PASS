<script setup lang="ts">
import type { KaraokeResponse } from "@/client";
import { karaokeDateLabel, isKaraokeToday } from "@/utils/karaoke";
import Card from "./card.vue";

const props = defineProps<{
    items: KaraokeResponse[];
    pending: boolean;
    hasMore?: boolean;
}>();
defineEmits<{ select: [item: KaraokeResponse] }>();

// 서버가 date, time 순으로 정렬해 내려주므로 순서를 유지한 채 같은 날짜끼리 묶는다.
// 런타임에서 date 필드는 "YYYY-MM-DD" 문자열이므로 String()으로 키를 만든다.
const groups = computed(() => {
    const map = new Map<string, KaraokeResponse[]>();
    for (const item of props.items) {
        const key = String(item.date);
        if (!map.has(key)) map.set(key, []);
        map.get(key)!.push(item);
    }
    return [...map.entries()].map(([date, list]) => ({ date, items: list }));
});
</script>

<template>
    <div class="flex-1 flex flex-col gap-2">
        <template v-if="pending">
            <USkeleton v-for="i in 4" :key="i" class="w-full h-18 rounded-2xl" />
        </template>
        <div
            class="flex-1 flex flex-col items-center justify-center text-ui-p1 opacity-50 py-16"
            v-else-if="items.length <= 0"
        >
            <UIcon name="i-ph-calendar-blank" class="text-h2 mb-1.5" />
            등록된 경매가 없어요.
        </div>
        <template v-else>
            <section v-for="group in groups" :key="group.date" class="flex flex-col gap-2 not-first:mt-3">
                <div class="flex items-center gap-1.5 px-1">
                    <p class="text-p1 font-bold">{{ karaokeDateLabel(group.date) }}</p>
                    <p class="text-ui-p2 light:text-black/50 dark:text-white/50" v-if="isKaraokeToday(group.date)">
                        오늘
                    </p>
                </div>
                <Card
                    v-for="item in group.items"
                    :key="item.id!"
                    :item="item"
                    @click="$emit('select', item)"
                />
            </section>
            <p class="text-ui-p2 light:text-black/50 dark:text-white/50 text-center py-4" v-if="!hasMore">
                더이상 없어요
            </p>
        </template>
    </div>
</template>
