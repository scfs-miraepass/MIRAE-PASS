<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { UserPermission } from '@/client'

const props = defineProps<{
    users: string[]
}>()

const session = useSession()

const canGrant = computed(() => ((session.value?.permissions || 0) & UserPermission._GRANT_POINT) === UserPermission._GRANT_POINT)
const canDeduct = computed(() => ((session.value?.permissions || 0) & UserPermission._DEDUCT_POINT) === UserPermission._DEDUCT_POINT)

const typeOptions = computed(() => {
    const options = []
    if (canGrant.value) {
        options.push({ label: '지급', value: 'grant' })
    }
    if (canDeduct.value) {
        options.push({ label: '차감', value: 'deduct' })
    }
    return options
})

const emit = defineEmits(['close', 'success'])

const open = ref<boolean>(true);
const loading = ref<boolean>(false);
const toast = useToast()

const form = ref({
    type: 'grant', // will be overwritten by watch below if needed
    amount: 0,
    reason: ''
})

watch(typeOptions, (options) => {
    if (options.length > 0 && !options.find(o => o.value === form.value.type)) {
        form.value.type = options[0]!.value
    }
}, { immediate: true })

watch(open, value => {
    if (!value) {
        setTimeout(() => emit('close'), 200)
    }
})

const onSubmit = async () => {
    if (form.value.amount <= 0) {
        toast.add({
            title: '포인트를 확인해주세요.',
            description: '포인트는 0보다 커야 합니다.',
            color: 'error'
        })
        return
    }
    
    if (!form.value.reason) {
        toast.add({
            title: '사유를 입력해주세요.',
            description: '포인트 변동 사유를 입력해야 합니다.',
            color: 'error'
        })
        return
    }

    loading.value = true
    const finalAmount = form.value.type === 'grant' ? form.value.amount : -form.value.amount;
    
    const req = await $API.updateUsersPointAdminPointPost({
        body: {
            user_ids: props.users.map(u => Number(u)),
            amount: finalAmount,
            reason: form.value.reason
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
        description: `${props.users.length}명의 유저에게 포인트가 적용되었습니다.`,
        color: 'success'
    })

    open.value = false
    emit('success')
}
</script>

<template>
    <UModal
        :title="`${users.length}명의 포인트 관리`"
        description="선택한 사용자들에게 일괄적으로 포인트를 지급하거나 차감합니다."
        v-model:open="open"
        :close="false"
        :dismissible="!loading"
    >
        <template #body>
            <form @submit.prevent="onSubmit" class="space-y-4">
                <div class="flex gap-4">
                    <UFormField label="유형" name="type">
                        <USelect
                            v-model="form.type"
                            :items="typeOptions"
                            class="w-20"
                        />
                    </UFormField>
                    <UFormField label="포인트" name="amount" class="w-2/3">
                        <UInput v-model="form.amount" type="number" min="1" placeholder="금액 입력" />
                    </UFormField>
                </div>
                
                <UFormField label="사유" name="reason">
                    <UInput v-model="form.reason" placeholder="포인트 변동 사유 (예: 이벤트 참여, 벌점 등)" class="w-full" />
                </UFormField>
            </form>
        </template>
        <template #footer>
            <div class="flex justify-end gap-2 w-full">
                <UButton label="취소" color="neutral" variant="ghost" :disabled="loading" @click="open = false" />
                <UButton label="적용" :color="form.type === 'grant' ? 'success' : 'error'" :loading="loading" @click="onSubmit" />
            </div>
        </template>
    </UModal>
</template>
