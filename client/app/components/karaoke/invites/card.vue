<script setup lang="ts">
defineProps<{
    leaderName: string;
    dateLabel: string;
    timeLabel: string;
    deciding: boolean;
}>();
defineEmits<{ decide: [accept: boolean] }>();
</script>

<template>
    <div class="w-full rounded-2xl light:bg-default dark:bg-muted px-5 py-4">
        <p class="text-p1 mb-1.5">{{ leaderName }}님의 파티</p>
        <p class="text-ui-p2 light:text-black/50 dark:text-white/50 mt-1">
            {{ dateLabel }} {{ timeLabel }} 노래방 예약
        </p>
        <div class="flex gap-2 mt-6">
            <UButton
                class="rounded-xl justify-center flex-1"
                color="neutral"
                variant="soft"
                :disabled="deciding"
                @click="$emit('decide', false)"
            >
                거절
            </UButton>
            <UButton class="rounded-xl justify-center flex-1" :disabled="deciding" @click="$emit('decide', true)">
                수락
            </UButton>
        </div>
    </div>
</template>
