<script setup lang="ts">
import type { DutchPayShare } from "@/utils/karaoke";

const amount = defineModel<number>("amount", { required: true });
const props = defineProps<{
    minBid: number;
    isValid: boolean;
    bidding: boolean;
    dutchPreview: DutchPayShare | null;
}>();
defineEmits<{ submit: [] }>();

const increase = () => {
    amount.value += KARAOKE_BID_UNIT;
};
const decrease = () => {
    amount.value = Math.max(props.minBid, amount.value - KARAOKE_BID_UNIT);
};
</script>

<template>
    <div class="flex-1 rounded-2xl light:bg-default dark:bg-muted p-6 flex flex-col">
        <div class="flex flex-col items-center flex-1 justify-center">
            <div class="flex items-center">
                <span class="text-h2 font-bold">{{amount.toLocaleString() }}</span>
                <span class="text-h4">P</span>
            </div>
            <p
                v-if="dutchPreview"
                class="text-ui-p2 mt-2 px-3 py-1.5 rounded-xl dark:bg-muted light:text-black/45 dark:text-white/40"
            >
                나 {{ dutchPreview.leaderShare.toLocaleString() }}P · 팀원 1인당 {{ dutchPreview.perMember.toLocaleString() }}P
            </p>

            <div class="space-x-3 mt-5">
                <UButton icon="i-ph-plus" variant="subtle" size="xl" class="rounded-lg" @click="increase" />
                <UButton
                    icon="i-ph-minus"
                    color="error"
                    variant="subtle"
                    size="xl"
                    class="rounded-lg"
                    :disabled="amount <= minBid"
                    @click="decrease"
                />
            </div>
        </div>

        <p class="text-ui-p2 light:text-black/50 dark:text-white/50 text-center mb-4">{{ minBid.toLocaleString() }}P 이상 입찰할 수 있어요</p>
        <UButton
            class="rounded-2xl justify-center flex py-4.5 transition-opacity mt-auto"
            :disabled="!isValid"
            :loading="bidding"
            @click="$emit('submit')"
        >
            <p class="text-p0">
                입찰하기
            </p>
        </UButton>
    </div>
</template>
