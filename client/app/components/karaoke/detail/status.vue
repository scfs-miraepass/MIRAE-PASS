<script setup lang="ts">
import type { KaraokeSocketBid } from "@/composables/useKaraokeSocket";
import { KaraokeStatus } from "@/client";
import { karaokeStatusLabel, formatDuration } from "@/utils/karaoke";

defineProps<{
    status: KaraokeStatus | undefined;
    remainingTime: number;
    minPoint: number;
    highestAmount: number | null;
    highestBid: KaraokeSocketBid | null | undefined;
}>();
</script>

<template>
    <div class="rounded-2xl light:bg-default dark:bg-muted p-5 flex flex-col items-center justify-center">
        <UBadge
            :color="status === KaraokeStatus.IN_PROGRESS ? 'primary' : 'warning'"
            variant="subtle"
            class="rounded-full mb-3"
        >
            {{ karaokeStatusLabel(status) }}
        </UBadge>

        <template v-if="status === KaraokeStatus.PENDING">
            <p class="text-ui-p2 light:text-black/50 dark:text-white/50">시작까지</p>
            <p class="text-h4 font-bold my-1">{{ formatDuration(remainingTime) }}</p>
            <p class="text-ui-p2 light:text-black/50 dark:text-white/50">
                최소 입찰가 {{ minPoint.toLocaleString() }}P
            </p>
        </template>
        <template v-else>
            <p class="text-ui-p2 light:text-black/50 dark:text-white/50">종료까지</p>
            <p class="text-h5 font-bold my-1">{{ formatDuration(remainingTime) }}</p>
            <div class="flex items-center gap-1.5 text-p1 font-bold">
                <UIcon name="i-ph-crown-simple-fill" v-if="highestAmount != null" />
                <template v-if="highestAmount != null">{{ highestAmount.toLocaleString() }}P</template>
                <template v-else>입찰 없음</template>
            </div>
            <p class="text-ui-p2 light:text-black/50 dark:text-white/50 mt-0.5" v-if="highestBid">
                {{ highestBid.bidder?.name ?? "알 수 없음" }}
                {{ highestBid.party_id ? "(파티)" : "" }} 최고가
            </p>
        </template>
    </div>
</template>
