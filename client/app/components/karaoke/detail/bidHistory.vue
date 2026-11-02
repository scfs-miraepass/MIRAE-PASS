<script setup lang="ts">
import type { KaraokeSocketBid } from "@/composables/useKaraokeSocket";

// 화면에는 최근 입찰만 보여주고, 전체 기록은 bids prop으로 그대로 유지한다 (최신순으로 정렬되어 내려온다).
const RECENT_BID_COUNT = 3;

const props = defineProps<{
    bids: KaraokeSocketBid[];
}>();

const recentBids = computed(() => props.bids.slice(0, RECENT_BID_COUNT));
</script>

<template>
    <div class="rounded-2xl light:bg-default dark:bg-muted p-6 flex flex-col overflow-y-auto min-h-38">
        <div class="flex-1 flex flex-col items-center justify-center text-p1 my-auto light:text-black/50 dark:text-white/50" v-if="recentBids.length <= 0">
            아직 입찰이 없어요
        </div>
        <TransitionGroup v-else tag="div" name="bid" class="relative flex flex-col gap-y-5">
            <div
                v-for="bid in recentBids"
                :key="bid.id"
                class="flex items-center justify-between"
            >
                <p class="text-p1">
                    {{ bid.bidder?.name ?? "알 수 없음" }}
                    <span class="text-p2 light:text-black/50 dark:text-white/50 " v-if="bid.party_id">파티</span>
                </p>
                <p class="text-p1 font-bold">{{ bid.amount.toLocaleString() }}P</p>
            </div>
        </TransitionGroup>
    </div>
</template>

<style scoped>
.bid-enter-active,
.bid-move {
    transition: all 0.3s ease;
}
.bid-leave-active {
    transition: all 0.2s ease;
    position: absolute;
    width: 100%;
}
.bid-enter-from {
    opacity: 0;
    transform: translateY(-12px);
}
.bid-leave-to {
    opacity: 0;
}
</style>
