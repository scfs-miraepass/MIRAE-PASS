<script setup lang="ts">
import type { KaraokeResponse } from '@/client'
import { karaokeTimeLabel } from '@/utils/karaoke'

const { karaoke } = defineProps<{
    karaoke: KaraokeResponse
}>()
const open = ref<boolean>(true)
const loading = ref<boolean>(false)
const emit = defineEmits(['close', 'delete'])
const toast = useToast()

watch(open, value => {
    if (!value) {
        setTimeout(() => emit('close'), 200)
    }
})

const onDelete = async () => {
    loading.value = true
    const req = await $API.deleteKaraoke({
        path: {
            karaoke_id: karaoke.id!
        }
    })

    if (req.error) {
        toast.add({
            title: '문제가 발생했습니다.',
            description: `지속적으로 발생하는 경우 관리자에게 문의 바랍니다.`,
            color: 'error'
        })
        loading.value = false
        return
    }

    toast.add({
        title: '정상적으로 처리되었습니다.',
        description: '경매가 삭제되었습니다. 진행중이던 입찰이 있었다면 자동으로 취소/환불됩니다.',
        color: 'success'
    })

    open.value = false
    emit('delete')
}
</script>

<template>
    <UModal
        :title="`${String(karaoke.date)} ${karaokeTimeLabel(karaoke.time)} 경매를 삭제하시겠습니까?`"
        description="이미 입찰이 있었던 경우 서버에서 자동으로 취소 및 환불 처리됩니다. 삭제 후에는 되돌릴 수 없습니다."
        :close="false"
        v-model:open="open"
        :ui="{ footer: 'justify-end' }"
        :dismissible="!loading"
    >
        <template #footer>
            <UButton label="삭제" color="error" variant="outline" class="cursor-pointer" :loading="loading" @click="onDelete" />
            <UButton label="취소" color="neutral" class="cursor-pointer" :disabled="loading" @click="open = false" />
        </template>
    </UModal>
</template>
