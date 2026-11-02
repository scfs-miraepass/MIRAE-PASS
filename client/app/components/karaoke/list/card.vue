<script setup lang="ts">
import type { KaraokeResponse } from "@/client";
import { karaokeTimeLabel, karaokeStatusLabel } from "@/utils/karaoke";

defineProps<{
    item: KaraokeResponse;
}>();
defineEmits<{ click: [] }>();
</script>

<template>
    <button
        class="w-full rounded-2xl light:bg-default dark:bg-muted px-5 py-4 flex items-center justify-between transition-all active:scale-95 active:opacity-70"
        @click="$emit('click')"
    >
        <div class="flex flex-col items-start">
            <p class="text-p1 font-bold">{{ karaokeTimeLabel(item.time) }}</p>
            <p class="text-ui-p2 light:text-black/50 dark:text-white/50 mt-1">
                {{ new Date(item.start_time).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" }) }}
                ~
                {{ new Date(item.end_time).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" }) }}
            </p>
        </div>
        <div class="flex flex-col items-end">
            <UBadge
                :color="item.status === 'In_Progress' ? 'primary' : item.status === 'Confirmed' ? 'neutral' : 'warning'"
                variant="subtle"
                class="rounded-full"
            >
                {{ karaokeStatusLabel(item.status) }}
            </UBadge>
            <p class="text-ui-p2 light:text-black/50 dark:text-white/50 mt-1.5">
                <template v-if="item.status === 'In_Progress' && item.highest_bid != null">
                    {{ item.highest_bid.toLocaleString() }}P
                </template>
                <template v-else-if="item.status === 'In_Progress'"> 입찰 없음 </template>
                <template v-else-if="item.status === 'Confirmed'"> 마감됨 </template>
                <template v-else> 시작 전 </template>
            </p>
        </div>
    </button>
</template>
