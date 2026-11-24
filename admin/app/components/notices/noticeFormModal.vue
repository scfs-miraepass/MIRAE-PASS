<script setup lang="ts">
import {
    NOTICE_CONTENT_KIND,
    NOTICE_TEXT_MAX_LENGTH,
    NOTICE_TITLE_MAX_LENGTH,
    emptyPollForm,
    noticeErrorMessage,
    pollFormError,
    toPollForm,
    toPollOperation,
    type ManagedNotice,
} from "~/utils/notice";

import PollFields from "~/components/notices/noticePollFields.vue";

// notice가 있으면 수정, 없으면 새 공지 작성
const { notice } = defineProps<{
    notice?: ManagedNotice;
}>();
// refresh: 공지는 저장했지만 설문 저장에 실패해 모달을 열어 둔 채 목록만 갱신할 때
const emit = defineEmits(["close", "success", "refresh"]);
const toast = useToast();

const open = ref<boolean>(true);
const loading = ref<boolean>(false);
const title = ref(notice?.title ?? "");
const text = ref(notice?.text ?? "");

// 설문. 수정 모드에서 설문이 있으면 열 때 불러온다.
const hadPoll = notice?.hasPoll ?? false;
const pollEnabled = ref(hadPoll);
const pollForm = ref(emptyPollForm());
const pollVoterCount = ref(0);
const pollLoading = ref(hadPoll);
// 기존 설문을 불러오지 못하면 덮어쓰거나 지우지 않도록 설문은 건드리지 않고 공지만 저장한다.
const pollLoadFailed = ref(false);

const pollError = computed(() => (pollEnabled.value && !pollLoadFailed.value ? pollFormError(pollForm.value) : null));
const canSubmit = computed(() => !!title.value.trim() && !!text.value.trim() && !pollLoading.value && !pollError.value);

onMounted(async () => {
    if (!notice || !hadPoll) return;
    const req = await $API.getPollPostsPostIdPollGet({ path: { post_id: notice.id } });
    if (req.error || !req.data.data) {
        pollLoadFailed.value = true;
    } else {
        pollForm.value = toPollForm(req.data.data);
        pollVoterCount.value = req.data.data.voter_count ?? 0;
    }
    pollLoading.value = false;
});

watch(open, (value) => {
    if (!value) setTimeout(() => emit("close"), 200);
});

// 설문 저장(또는 삭제). 실패하면 오류 메시지를 돌려준다.
async function savePoll(postId: number): Promise<string | null> {
    if (pollLoadFailed.value) return null;
    if (pollEnabled.value) {
        const req = await $API.setPollPostsPostIdPollPut({ path: { post_id: postId }, body: toPollOperation(pollForm.value) });
        return req.error ? noticeErrorMessage(req.error, "설문을 저장하지 못했습니다.") : null;
    }
    if (hadPoll) {
        const req = await $API.deletePollPostsPostIdPollDelete({ path: { post_id: postId } });
        return req.error ? noticeErrorMessage(req.error, "설문을 삭제하지 못했습니다.") : null;
    }
    return null;
}

async function onSubmit() {
    if (loading.value || !canSubmit.value) return;
    loading.value = true;

    const body = { title: title.value.trim(), content_data: { kind: NOTICE_CONTENT_KIND, text: text.value.trim() } };

    if (!notice) {
        // 새 공지는 설문과 함께 한 번에 만든다. (서버가 같은 트랜잭션에서 처리)
        const req = await $API.createPostPostsPost({
            body: { ...body, poll: pollEnabled.value ? toPollOperation(pollForm.value) : null },
        });
        if (req.error) {
            toast.add({
                title: "공지를 게시하지 못했습니다.",
                description: "지속적으로 발생하는 경우 관리자에게 문의 바랍니다.",
                color: "error",
            });
            loading.value = false;
            return;
        }
        toast.add({ title: "공지를 게시했습니다.", color: "success" });
        open.value = false;
        emit("success");
        return;
    }

    const req = await $API.updatePostPostsPostIdPatch({ path: { post_id: notice.id }, body });
    if (req.error) {
        toast.add({
            title: "공지를 수정하지 못했습니다.",
            description: "지속적으로 발생하는 경우 관리자에게 문의 바랍니다.",
            color: "error",
        });
        loading.value = false;
        return;
    }

    const pollFailure = await savePoll(notice.id);
    if (pollFailure) {
        // 공지 내용은 이미 저장되었으므로 목록은 갱신하고, 모달은 열어 둔 채 설문만 다시 시도할 수 있게 한다.
        toast.add({ title: "공지는 저장했지만 설문을 저장하지 못했습니다.", description: pollFailure, color: "error" });
        loading.value = false;
        emit("refresh");
        return;
    }

    toast.add({ title: "공지를 수정했습니다.", color: "success" });
    open.value = false;
    emit("success");
}
</script>

<template>
    <UModal
        :title="notice ? '공지 수정' : '새 공지 작성'"
        :description="notice ? '수정한 내용은 학생 앱에 바로 반영됩니다.' : '게시하면 학생 앱 홈과 공지 목록에 바로 표시됩니다.'"
        v-model:open="open"
        :close="false"
        :dismissible="!loading"
        :ui="{ content: 'sm:max-w-2xl' }"
    >
        <template #body>
            <form id="notice-form" class="space-y-4" @submit.prevent="onSubmit">
                <UFormField label="제목" name="title" required :hint="`${title.length}/${NOTICE_TITLE_MAX_LENGTH}`">
                    <UInput
                        v-model="title"
                        class="w-full"
                        placeholder="공지 제목을 입력해주세요."
                        :maxlength="NOTICE_TITLE_MAX_LENGTH"
                        :disabled="loading"
                        autofocus
                    />
                </UFormField>
                <UFormField label="내용" name="text" required :hint="`${text.length}/${NOTICE_TEXT_MAX_LENGTH}`">
                    <UTextarea
                        v-model="text"
                        class="w-full"
                        placeholder="학생들에게 전달할 내용을 입력해주세요. 줄바꿈은 그대로 표시됩니다."
                        :rows="10"
                        autoresize
                        :maxrows="20"
                        :maxlength="NOTICE_TEXT_MAX_LENGTH"
                        :disabled="loading"
                    />
                </UFormField>

                <USeparator />

                <div class="space-y-3">
                    <div class="flex items-center justify-between gap-4">
                        <div>
                            <p class="font-medium text-highlighted">설문</p>
                            <p class="text-sm text-muted">공지 아래에 객관식 질문을 붙여 학생들의 응답을 받습니다.</p>
                        </div>
                        <USwitch v-model="pollEnabled" :disabled="loading || pollLoading || pollLoadFailed" aria-label="설문 사용" />
                    </div>

                    <div v-if="pollLoading" class="space-y-2">
                        <USkeleton class="h-8 w-full" />
                        <USkeleton class="h-8 w-2/3" />
                    </div>
                    <UAlert
                        v-else-if="pollLoadFailed"
                        color="warning"
                        variant="subtle"
                        icon="i-lucide-triangle-alert"
                        title="설문을 불러오지 못했습니다."
                        description="공지 내용만 저장되며 설문은 바뀌지 않습니다."
                    />
                    <template v-else-if="pollEnabled">
                        <PollFields v-model="pollForm" :disabled="loading" :options-locked="pollVoterCount > 0" />
                        <p v-if="pollError" class="text-sm text-error">{{ pollError }}</p>
                    </template>
                    <UAlert
                        v-else-if="hadPoll"
                        color="error"
                        variant="subtle"
                        icon="i-lucide-trash-2"
                        title="저장하면 설문이 삭제됩니다."
                        :description="pollVoterCount > 0 ? `받은 응답 ${pollVoterCount}명의 기록도 함께 삭제되며 되돌릴 수 없습니다.` : '되돌릴 수 없습니다.'"
                    />
                </div>
            </form>
        </template>
        <template #footer>
            <div class="flex w-full justify-end gap-2">
                <UButton label="취소" color="neutral" variant="ghost" class="cursor-pointer" :disabled="loading" @click="open = false" />
                <UButton
                    type="submit"
                    form="notice-form"
                    :label="notice ? '저장' : '게시하기'"
                    :icon="notice ? 'i-lucide-check' : 'i-lucide-send'"
                    class="cursor-pointer"
                    :loading="loading"
                    :disabled="!canSubmit"
                />
            </div>
        </template>
    </UModal>
</template>
