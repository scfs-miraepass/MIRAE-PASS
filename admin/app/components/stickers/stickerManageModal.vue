<script setup lang="ts">
import { ref, watch, computed } from "vue";
import type { User, StickerBalance } from "@miraepass/api-client";

const props = defineProps<{
    user: User;
    mode: "grant" | "revoke";
    balance: StickerBalance;
}>();

const emit = defineEmits(["close", "success"]);

const open = ref<boolean>(true);
const loading = ref<boolean>(false);
const toast = useToast();

const isGrant = computed(() => props.mode === "grant");
const actionLabel = computed(() => (isGrant.value ? "지급" : "회수"));
const targetLabel = computed(() => (props.user.type === "teacher" ? "선생님" : "학생"));
// 지급은 남은 한도까지, 회수는 보유 수까지 선택 가능
const limit = computed(() =>
    isGrant.value ? Math.max(0, props.balance.max - props.balance.count) : props.balance.count,
);
const amountOptions = computed(() =>
    Array.from({ length: limit.value }, (_, i) => ({ label: `${i + 1}개`, value: i + 1 })),
);

const form = ref({
    amount: 1,
    memo: "",
});

watch(limit, (value) => {
    if (form.value.amount > value) form.value.amount = Math.max(1, value);
}, { immediate: true });

watch(open, (value) => {
    if (!value) {
        setTimeout(() => emit("close"), 200);
    }
});

const onSubmit = async () => {
    if (form.value.amount <= 0 || form.value.amount > limit.value) {
        toast.add({
            title: "수량을 확인해주세요.",
            description: `최대 ${limit.value}개까지 ${actionLabel.value}할 수 있습니다.`,
            color: "error",
        });
        return;
    }

    loading.value = true;
    const body = {
        user_id: props.user.id!,
        amount: form.value.amount,
        memo: form.value.memo || undefined,
    };
    const req = isGrant.value
        ? await $API.grantSticker({ body })
        : await $API.revokeSticker({ body });

    if (req.error) {
        toast.add({
            title: `${actionLabel.value} 실패`,
            description: stickerErrorMessage(req.error),
            color: "error",
        });
        loading.value = false;
        return;
    }

    toast.add({
        title: "정상적으로 처리되었습니다.",
        description: `${props.user.name} ${targetLabel.value}에게 스티커 ${form.value.amount}개를 ${actionLabel.value}했습니다. (현재 ${req.data.data.count}개)`,
        color: "success",
    });

    open.value = false;
    emit("success", req.data.data);
};
</script>

<template>
    <UModal
        :title="`스티커 ${actionLabel}`"
        :description="`${user.name} (${user.id}) · 현재 ${balance.count} / ${balance.max}개 보유`"
        v-model:open="open"
        :close="false"
        :dismissible="!loading"
    >
        <template #body>
            <form @submit.prevent="onSubmit" class="space-y-4">
                <UFormField label="수량" name="amount">
                    <USelect
                        v-model="form.amount"
                        :items="amountOptions"
                        :disabled="amountOptions.length === 0"
                        class="w-28"
                    />
                </UFormField>
                <UFormField label="메모 (선택)" name="memo">
                    <UInput v-model="form.memo" maxlength="100" placeholder="예: 수업 태도 우수" class="w-full" />
                </UFormField>
            </form>
        </template>
        <template #footer>
            <div class="flex justify-end gap-2 w-full">
                <UButton label="취소" color="neutral" variant="ghost" :disabled="loading" @click="open = false" />
                <UButton
                    :label="actionLabel"
                    :color="isGrant ? 'success' : 'error'"
                    :loading="loading"
                    :disabled="amountOptions.length === 0"
                    @click="onSubmit"
                />
            </div>
        </template>
    </UModal>
</template>
