<script setup lang="ts">
import type { KaraokePartyDetail } from "@/client";
import type { DutchPayShare } from "@/utils/karaoke";
import Section from "~/components/setting/section.vue";
import PageButton from "~/components/setting/object.vue";

defineProps<{
    karaokeId: number;
    party: KaraokePartyDetail | null;
    isLeader: boolean;
    partyHeadcount: number;
    dutchPreview: DutchPayShare | null;
    creatingParty: boolean;
}>();
defineEmits<{ create: [] }>();
</script>

<template>
    <Section>
        <div v-if="!party" class="flex items-center justify-between gap-2 px-5.5 py-3">
            <p class="text-ui-p2 leading-4.5 light:text-black/60 dark:text-white/60">혼자 입찰하거나, <br />파티를 만들어 함께 낼 수 있어요.</p>
            <UButton size="lg" class="rounded-lg shrink-0" :loading="creatingParty" @click="$emit('create')">파티 만들기</UButton>
        </div>

        <NuxtLink v-else :to="`/karaoke/${karaokeId}/party`" v-slot="{ navigate }" custom>
            <PageButton @click="navigate()" :label="isLeader ? `내 파티 (${partyHeadcount}명)` : `${party.leader.name}님의 파티`">
                <template #value>
                    <template v-if="!isLeader">
                        파티장만 입찰할 수 있어요.
                    </template>
                </template>
            </PageButton>
        </NuxtLink>
    </Section>
</template>
