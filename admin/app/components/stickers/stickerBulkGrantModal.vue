<script setup lang="ts">
import { ref, watch, computed } from "vue";

const props = defineProps<{
    users: string[];
}>();

const emit = defineEmits(["close", "success"]);

const STICKER_MAX = 3;

const open = ref<boolean>(true);
const loading = ref<boolean>(false);
const toast = useToast();

const amountOptions = computed(() =>
    Array.from({ length: STICKER_MAX }, (_, i) => ({ label: `${i + 1}개`, value: i + 1 })),
);

const form = ref({
    amount: 1,
    memo: "",
});

watch(open, (value) => {
    if (!value) {
        setTimeout(() => emit("close"), 200);
    }
});

const onSubmit = async () => {
    loading.value = true;
    const req = await $API.grantStickers({
        body: {
            user_ids: props.users.map((u) => Number(u)),
            amount: form.value.amount,
            memo: form.value.memo || undefined,
        },
    });

    if (req.error) {
        toast.add({
            title: "지급 실패",
            description: stickerErrorMessage(req.error),
            color: "error",
        });
        loading.value = false;
        return;
    }

    const { succeeded, failed } = req.data.data;
    // 이번 주 남은 한도 때문에 요청보다 적게 받은 사용자
    const partial = succeeded.filter((item) => item.granted < form.value.amount);
    if (succeeded.length > 0) {
        toast.add({
            title: "정상적으로 처리되었습니다.",
            description: partial.length > 0
                ? `${succeeded.length}명에게 지급했습니다. 그중 ${partial.length}명은 남은 한도만큼만 받았습니다. (${partial.map((p) => `${p.user_id}: ${p.granted}개`).join(", ")})`
                : `${succeeded.length}명에게 스티커 ${form.value.amount}개씩 지급했습니다.`,
            color: "success",
        });
    }
    if (failed.length > 0) {
        toast.add({
            title: `${failed.length}명은 지급하지 못했습니다.`,
            description: failed.map((f) => `${f.user_id}: ${f.reason}`).join("\n"),
            color: succeeded.length > 0 ? "warning" : "error",
        });
    }

    open.value = false;
    emit("success");
};
</script>

<template>
    <UModal
        :title="`${users.length}명에게 스티커 지급`"
        :description="`선택한 사용자들에게 스티커를 지급합니다. 이번 주 남은 한도가 적은 사용자는 남은 만큼만 받고, 한도(${STICKER_MAX}개)를 다 채운 사용자는 건너뜁니다.`"
        v-model:open="open"
        :close="false"
        :dismissible="!loading"
    >
        <template #body>
            <form @submit.prevent="onSubmit" class="space-y-4">
                <UFormField label="수량 (1인당 최대)" name="amount">
                    <USelect v-model="form.amount" :items="amountOptions" class="w-28" />
                </UFormField>
                <UFormField label="메모 (선택)" name="memo">
                    <UInput v-model="form.memo" maxlength="100" placeholder="예: 체육대회 우수 참여" class="w-full" />
                </UFormField>
            </form>
        </template>
        <template #footer>
            <div class="flex justify-end gap-2 w-full">
                <UButton label="취소" color="neutral" variant="ghost" :disabled="loading" @click="open = false" />
                <UButton label="지급" color="success" :loading="loading" @click="onSubmit" />
            </div>
        </template>
    </UModal>
</template>
