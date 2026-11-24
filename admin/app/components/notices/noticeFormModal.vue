<script setup lang="ts">
import { NOTICE_CONTENT_KIND, NOTICE_TEXT_MAX_LENGTH, NOTICE_TITLE_MAX_LENGTH, type ManagedNotice } from "~/utils/notice";

// notice가 있으면 수정, 없으면 새 공지 작성
const { notice } = defineProps<{
    notice?: ManagedNotice;
}>();
const emit = defineEmits(["close", "success"]);
const toast = useToast();

const open = ref<boolean>(true);
const loading = ref<boolean>(false);
const title = ref(notice?.title ?? "");
const text = ref(notice?.text ?? "");
const canSubmit = computed(() => !!title.value.trim() && !!text.value.trim());

watch(open, (value) => {
    if (!value) setTimeout(() => emit("close"), 200);
});

async function onSubmit() {
    if (loading.value || !canSubmit.value) return;
    loading.value = true;

    const body = { title: title.value.trim(), content_data: { kind: NOTICE_CONTENT_KIND, text: text.value.trim() } };
    const req = notice
        ? await $API.updatePostPostsPostIdPatch({ path: { post_id: notice.id }, body })
        : await $API.createPostPostsPost({ body });

    if (req.error) {
        toast.add({
            title: notice ? "공지를 수정하지 못했습니다." : "공지를 게시하지 못했습니다.",
            description: "지속적으로 발생하는 경우 관리자에게 문의 바랍니다.",
            color: "error",
        });
        loading.value = false;
        return;
    }

    toast.add({ title: notice ? "공지를 수정했습니다." : "공지를 게시했습니다.", color: "success" });
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
