<script setup lang="ts">
import type { PollResponse } from "@miraepass/api-client";

const { postId } = defineProps<{
    postId: number;
}>();

const toast = useToast();

const { data: poll, status, error, refresh } = useAsyncData(
    `notices.poll.${postId}`,
    async (_nuxtApp, { signal }) => {
        const req = await $API.getPollPostsPostIdPollGet({ path: { post_id: postId }, signal });
        if (req.error || !req.data.data) throw createError({ statusCode: req.response?.status ?? 503 });
        return req.data.data;
    },
    { server: false },
);

const loading = computed(() => status.value === "idle" || status.value === "pending");
const answered = computed(() => (poll.value?.my_option_ids.length ?? 0) > 0);
// 응답했으면 기본은 '내 응답 보기' 상태이고, '응답 수정'을 누르면 다시 고를 수 있다.
const editing = ref(false);
const selected = ref<number[]>([]);
const submitting = ref(false);
const canSelect = computed(() => !!poll.value && !poll.value.closed && (!answered.value || editing.value) && !submitting.value);

watch(poll, (value) => {
    selected.value = [...(value?.my_option_ids ?? [])];
    editing.value = false;
});

function toggle(optionId: number) {
    if (!canSelect.value || !poll.value) return;
    if (poll.value.allow_multiple) {
        selected.value = selected.value.includes(optionId)
            ? selected.value.filter((id) => id !== optionId)
            : [...selected.value, optionId];
    } else {
        selected.value = [optionId];
    }
}

function applyResult(value: PollResponse | undefined) {
    if (value) poll.value = value;
    else refresh();
}

async function submit() {
    if (!poll.value || !selected.value.length || submitting.value) return;
    submitting.value = true;
    const req = await $API.votePollPostsPostIdPollVotePut({ path: { post_id: postId }, body: { option_ids: selected.value } });
    submitting.value = false;

    if (req.error) {
        toast.add({ title: "응답하지 못했어요.", description: noticeErrorMessage(req.error), color: "error" });
        // 마감되었거나 설문이 바뀐 경우 최신 상태로 다시 그린다.
        if (req.response?.status === 400 || req.response?.status === 404) refresh();
        return;
    }
    toast.add({ title: answered.value ? "응답을 수정했어요." : "응답했어요.", color: "success" });
    applyResult(req.data.data);
}

async function cancel() {
    if (submitting.value) return;
    submitting.value = true;
    const req = await $API.cancelPollVotePostsPostIdPollVoteDelete({ path: { post_id: postId } });
    submitting.value = false;

    if (req.error) {
        toast.add({ title: "응답을 취소하지 못했어요.", description: noticeErrorMessage(req.error), color: "error" });
        if (req.response?.status === 400 || req.response?.status === 404) refresh();
        return;
    }
    toast.add({ title: "응답을 취소했어요.", color: "success" });
    refresh();
}

function cancelEditing() {
    selected.value = [...(poll.value?.my_option_ids ?? [])];
    editing.value = false;
}
</script>

<template>
    <!-- 설문이 삭제된 경우(404)에는 아무것도 보여주지 않는다. -->
    <section
        v-if="!(error && error.statusCode === 404)"
        class="mt-3 rounded-2xl p-5 light:bg-default dark:bg-muted"
        aria-labelledby="notice-poll-question"
        :aria-busy="loading || submitting"
    >
        <div v-if="loading" role="status" aria-label="설문을 불러오는 중입니다.">
            <USkeleton class="mb-3 h-3.5 w-24 rounded-full light:bg-elevated dark:bg-accented/50" />
            <USkeleton class="mb-4 h-6 w-4/5 rounded-full light:bg-elevated dark:bg-accented/50" />
            <div class="space-y-2">
                <USkeleton v-for="i in 3" :key="i" class="h-13 w-full rounded-xl light:bg-elevated dark:bg-accented/50" />
            </div>
        </div>

        <div v-else-if="error" role="alert" class="flex flex-col items-center gap-3 py-4 text-center">
            <p class="text-ui-p1 opacity-50">{{ error.statusCode === 403 ? "설문을 볼 수 있는 권한이 없어요." : "설문을 불러오지 못했어요." }}</p>
            <UButton v-if="error.statusCode !== 403" color="neutral" variant="subtle" size="lg" @click="refresh()">다시 시도</UButton>
        </div>

        <template v-else-if="poll">
            <div class="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-ui-p2">
                <span class="flex items-center gap-1 font-bold text-primary">
                    <UIcon name="i-ph-list-checks-bold" aria-hidden="true" />
                    설문
                </span>
                <span
                    class="rounded-full px-2 py-0.5 text-p3 font-bold"
                    :class="poll.closed ? 'bg-accented light:text-black/50 dark:text-white/50' : 'bg-success/10 text-success'"
                >
                    {{ poll.closed ? "마감" : "진행 중" }}
                </span>
                <span v-if="poll.closes_at" class="light:text-black/50 dark:text-white/50">{{ pollClosesAtLabel(poll.closes_at) }} 마감</span>
            </div>

            <h2 id="notice-poll-question" class="text-p0 font-bold leading-snug break-words">{{ poll.question }}</h2>
            <p class="mt-1 text-ui-p2 light:text-black/50 dark:text-white/50">
                {{ poll.allow_multiple ? "여러 개를 고를 수 있어요." : "하나만 고를 수 있어요." }}
            </p>

            <div
                class="mt-4 space-y-2"
                :role="poll.allow_multiple ? 'group' : 'radiogroup'"
                aria-labelledby="notice-poll-question"
            >
                <button
                    v-for="option in poll.options"
                    :key="option.id"
                    type="button"
                    :role="poll.allow_multiple ? 'checkbox' : 'radio'"
                    :aria-checked="selected.includes(option.id)"
                    :aria-disabled="!canSelect"
                    class="flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left transition-all focus-visible:outline-2 focus-visible:outline-primary"
                    :class="[
                        selected.includes(option.id) ? 'border-primary bg-primary/10' : 'border-default dark:border-accented',
                        canSelect ? 'active:scale-[0.98] active:bg-accented' : 'cursor-default',
                    ]"
                    @click="toggle(option.id)"
                >
                    <UIcon
                        :name="selected.includes(option.id)
                            ? (poll.allow_multiple ? 'i-ph-check-square-fill' : 'i-ph-check-circle-fill')
                            : (poll.allow_multiple ? 'i-ph-square' : 'i-ph-circle')"
                        class="size-6 shrink-0"
                        :class="selected.includes(option.id) ? 'text-primary' : 'light:text-black/30 dark:text-white/30'"
                        aria-hidden="true"
                    />
                    <span class="min-w-0 flex-1 text-p1 font-normal break-words">{{ option.text }}</span>
                    <span v-if="option.votes != null" class="shrink-0 text-ui-p2 tabular-nums light:text-black/50 dark:text-white/50">{{ option.votes }}명</span>
                </button>
            </div>

            <p v-if="poll.voter_count != null" class="mt-3 text-ui-p2 light:text-black/50 dark:text-white/50">총 {{ poll.voter_count }}명이 응답했어요.</p>

            <!-- 마감 -->
            <p v-if="poll.closed" class="mt-4 text-center text-ui-p2 light:text-black/50 dark:text-white/50">
                {{ answered ? "마감된 설문이에요. 위에 표시된 것이 내 응답이에요." : "마감된 설문이에요." }}
            </p>

            <!-- 응답함, 보기 상태 -->
            <div v-else-if="answered && !editing" class="mt-4 space-y-2">
                <p class="flex items-center justify-center gap-1 text-ui-p2 text-success">
                    <UIcon name="i-ph-check-circle-fill" aria-hidden="true" />
                    응답했어요
                </p>
                <div class="flex gap-2">
                    <UButton color="neutral" variant="subtle" size="xl" block class="rounded-xl" :disabled="submitting" @click="editing = true">응답 수정</UButton>
                    <UButton color="neutral" variant="ghost" size="xl" block class="rounded-xl" :loading="submitting" @click="cancel">응답 취소</UButton>
                </div>
            </div>

            <!-- 응답 전 또는 수정 중 -->
            <div v-else class="mt-4 flex gap-2">
                <UButton v-if="editing" color="neutral" variant="ghost" size="xl" block class="rounded-xl" :disabled="submitting" @click="cancelEditing">취소</UButton>
                <UButton size="xl" block class="rounded-xl" :loading="submitting" :disabled="!selected.length" @click="submit">
                    {{ editing ? "수정하기" : "응답하기" }}
                </UButton>
            </div>
        </template>
    </section>
</template>
