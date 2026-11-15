<script setup lang="ts">
import { ref, watch } from 'vue'

const emit = defineEmits(['close', 'success'])

const open = ref<boolean>(true)
const loading = ref<boolean>(false)
const toast = useToast()

watch(open, value => {
    if (!value) {
        setTimeout(() => emit('close'), 200)
    }
})

const onSubmit = async () => {
    loading.value = true
    const req = await $API.resetStickers()

    if (req.error) {
        toast.add({
            title: '초기화 실패',
            description: '문제가 발생했습니다. 지속적으로 발생하는 경우 관리자에게 문의 바랍니다.',
            color: 'error'
        })
        loading.value = false
        return
    }

    toast.add({
        title: '스티커가 초기화되었습니다.',
        description: '모든 학생의 보유 스티커 수가 0이 되었습니다.',
        color: 'success'
    })

    open.value = false
    emit('success')
}
</script>

<template>
    <UModal
        title="스티커 수동 초기화"
        description="새 집계 기간을 시작합니다."
        v-model:open="open"
        :close="false"
        :dismissible="!loading"
    >
        <template #body>
            <p class="text-sm">
                모든 학생의 이번 기간 스티커 보유 수가 <span class="font-semibold">0</span>이 됩니다.
            </p>
            <p class="text-sm text-muted mt-1">
                지급/회수 기록은 삭제되지 않으며, 초기화 이후의 기록만 새 기간에 집계됩니다. 이 작업은 되돌릴 수 없습니다.
            </p>
        </template>
        <template #footer>
            <div class="flex justify-end gap-2 w-full">
                <UButton label="취소" color="neutral" variant="ghost" :disabled="loading" @click="open = false" />
                <UButton label="초기화" color="error" :loading="loading" @click="onSubmit" />
            </div>
        </template>
    </UModal>
</template>
