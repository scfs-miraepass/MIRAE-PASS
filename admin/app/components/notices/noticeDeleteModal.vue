<script setup lang="ts">
import type { ManagedNotice } from "~/utils/notice";

const { notice } = defineProps<{
    notice: ManagedNotice;
}>();
const emit = defineEmits(["close", "success"]);
const toast = useToast();

const open = ref<boolean>(true);
const loading = ref<boolean>(false);

watch(open, (value) => {
    if (!value) setTimeout(() => emit("close"), 200);
});

async function onDelete() {
    loading.value = true;
    const req = await $API.deletePostPostsPostIdDelete({ path: { post_id: notice.id } });

    if (req.error) {
        toast.add({
            title: "공지를 삭제하지 못했습니다.",
            description: "지속적으로 발생하는 경우 관리자에게 문의 바랍니다.",
            color: "error",
        });
        loading.value = false;
        return;
    }

    toast.add({ title: "공지를 삭제했습니다.", color: "success" });
    open.value = false;
    emit("success");
}
</script>

<template>
    <UModal
        :title="`'${notice.title}' 공지를 삭제하시겠습니까?`"
        description="학생 앱에서도 바로 사라지며, 삭제 후에는 되돌릴 수 없습니다."
        v-model:open="open"
        :close="false"
        :dismissible="!loading"
        :ui="{ title: 'break-all', footer: 'justify-end' }"
    >
        <template #footer>
            <UButton label="삭제" color="error" variant="outline" class="cursor-pointer" :loading="loading" @click="onDelete" />
            <UButton label="취소" color="neutral" class="cursor-pointer" :disabled="loading" @click="open = false" />
        </template>
    </UModal>
</template>
