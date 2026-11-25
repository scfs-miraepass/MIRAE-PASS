<script setup lang="ts">
import { pollClosesAtLabel, type ManagedNotice } from "~/utils/notice";

const { notice } = defineProps<{
    notice: ManagedNotice;
}>();
const emit = defineEmits(["close"]);

const open = ref<boolean>(true);

watch(open, (value) => {
    if (!value) setTimeout(() => emit("close"), 200);
});

const { data: poll, status, error, refresh } = useAsyncData(
    `notices.poll_result.${notice.id}`,
    async (_nuxtApp, { signal }) => {
        const req = await $API.getPollPostsPostIdPollGet({ path: { post_id: notice.id }, signal });
        if (req.error || !req.data.data) {
            throw createError({
                statusCode: req.response?.status ?? 503,
                statusMessage: req.response?.status === 404 ? "설문이 삭제되었습니다." : "설문 결과를 불러오지 못했습니다.",
            });
        }
        return req.data.data;
    },
    { server: false },
);

const loading = computed(() => status.value === "idle" || status.value === "pending");
const voterCount = computed(() => poll.value?.voter_count ?? 0);
// 복수 선택 설문은 선택지별 합이 응답자 수보다 클 수 있으므로, 비율은 응답자 수 기준으로 계산한다.
const ratio = (votes?: number | null) => (voterCount.value > 0 ? Math.round(((votes ?? 0) / voterCount.value) * 100) : 0);
</script>

<template>
    <UModal title="설문 결과" :description="notice.title" v-model:open="open" :ui="{ content: 'sm:max-w-xl' }">
        <template #body>
            <div v-if="loading" class="space-y-3">
                <USkeleton class="h-5 w-3/4" />
                <USkeleton v-for="i in 3" :key="i" class="h-10 w-full" />
            </div>

            <UAlert
                v-else-if="error"
                color="error"
                variant="subtle"
                icon="i-lucide-circle-alert"
                :title="error.statusMessage"
                :actions="error.statusCode === 404 ? [] : [{ label: '다시 시도', color: 'error', variant: 'outline', onClick: () => refresh() }]"
            />

            <div v-else-if="poll" class="space-y-4">
                <div>
                    <p class="font-medium text-highlighted">{{ poll.question }}</p>
                    <div class="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted">
                        <UBadge :color="poll.closed ? 'neutral' : 'success'" variant="subtle">{{ poll.closed ? "마감" : "진행 중" }}</UBadge>
                        <UBadge v-if="poll.allow_multiple" color="neutral" variant="outline">복수 선택</UBadge>
                        <span>마감: {{ pollClosesAtLabel(poll.closes_at) }}</span>
                    </div>
                </div>

                <ul class="space-y-3">
                    <li v-for="option in poll.options" :key="option.id">
                        <div class="mb-1 flex items-baseline justify-between gap-3 text-sm">
                            <span class="break-words text-highlighted">{{ option.text }}</span>
                            <span class="shrink-0 tabular-nums text-muted">{{ option.votes ?? 0 }}명 · {{ ratio(option.votes) }}%</span>
                        </div>
                        <UProgress :model-value="ratio(option.votes)" size="sm" />
                    </li>
                </ul>

                <p class="text-sm text-muted">
                    총 응답자 <span class="font-medium text-highlighted tabular-nums">{{ voterCount }}</span>명
                    <template v-if="poll.allow_multiple"> · 여러 개를 고를 수 있어 비율의 합이 100%를 넘을 수 있습니다.</template>
                </p>
            </div>
        </template>
        <template #footer>
            <div class="flex w-full justify-end gap-2">
                <UButton label="새로고침" icon="i-lucide-refresh-cw" color="neutral" variant="ghost" class="cursor-pointer" :loading="loading" @click="refresh()" />
                <UButton label="닫기" color="neutral" variant="soft" class="cursor-pointer" @click="open = false" />
            </div>
        </template>
    </UModal>
</template>
