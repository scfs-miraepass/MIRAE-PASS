<script setup lang="ts">
import { ref, watch } from 'vue'
import type { StickerHistoryItem } from '@miraepass/api-client'

const props = defineProps<{
    item: StickerHistoryItem
}>()

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
    const req = await $API.deleteStickerHistory({ path: { history_id: props.item.id } })

    if (req.error) {
        toast.add({
            title: '기록 취소 실패',
            description: req.response?.status === 409
                ? '이 기록을 취소하면 대상의 보유 수가 0 미만이 됩니다. 회수 기록을 먼저 취소해주세요.'
                : req.response?.status === 404
                    ? '이미 삭제된 기록입니다.'
                    : '문제가 발생했습니다. 지속적으로 발생하는 경우 관리자에게 문의 바랍니다.',
            color: 'error'
        })
        loading.value = false
        if (req.response?.status === 404) {
            open.value = false
            emit('success')
        }
        return
    }

    toast.add({
        title: '기록이 취소되었습니다.',
        description: props.item.class_grade != null
            ? `${props.item.user_name ?? props.item.user_id} 선생님의 ${props.item.class_grade}학년 ${props.item.class_number}반 전달 ${Math.abs(props.item.amount)}개 기록을 취소했습니다.`
            : `${props.item.user_name ?? props.item.user_id} ${props.item.user_type === 'teacher' ? '선생님' : '학생'}의 스티커 ${props.item.amount > 0 ? '지급' : '회수'} ${Math.abs(props.item.amount)}개 기록을 취소했습니다.`,
        color: 'success'
    })

    open.value = false
    emit('success')
}
</script>

<template>
    <UModal
        title="스티커 기록 취소"
        description="이 기록을 삭제해 변동을 없던 것으로 만듭니다."
        v-model:open="open"
        :close="false"
        :dismissible="!loading"
    >
        <template #body>
            <div class="text-sm space-y-1">
                <p>
                    <span class="font-semibold">{{ item.user_name ?? '-' }}</span>
                    <span class="text-muted ml-1">{{ item.user_id }}</span>
                </p>
                <p>
                    <UBadge v-if="item.class_grade != null" color="info" variant="subtle">
                        {{ item.class_grade }}학년 {{ item.class_number }}반에 전달 {{ -item.amount }}
                    </UBadge>
                    <UBadge v-else :color="item.amount > 0 ? 'success' : 'error'" variant="subtle">
                        {{ item.amount > 0 ? `+${item.amount}` : item.amount }}
                    </UBadge>
                    <span class="text-muted ml-2">{{ new Date(item.created_at).toLocaleString('ko-KR', { dateStyle: 'medium', timeStyle: 'short' }) }}</span>
                </p>
                <p v-if="item.memo" class="text-muted">메모: {{ item.memo }}</p>
            </div>
            <p class="text-sm text-muted mt-3">
                취소하면 기록이 삭제되고 대상의 보유 수가 그만큼 되돌아갑니다. 이 작업은 되돌릴 수 없습니다.
            </p>
        </template>
        <template #footer>
            <div class="flex justify-end gap-2 w-full">
                <UButton label="닫기" color="neutral" variant="ghost" :disabled="loading" @click="open = false" />
                <UButton label="기록 취소" color="error" :loading="loading" @click="onSubmit" />
            </div>
        </template>
    </UModal>
</template>
