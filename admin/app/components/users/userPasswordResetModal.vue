<script setup lang="ts">
import type { User } from '@/client'

const { user } = defineProps<{
    user: User
}>()
const open = ref<boolean>(true);
const loading = ref<boolean>(false);
const emit = defineEmits(['close'])
const toast = useToast()

watch(open, value => {
    if (!value) {
        setTimeout(() => emit('close'), 200)
    }
})

const resetPassword = async () => {
    loading.value = true
    const req = await $API.resetUserPasswordAdminUsersUserIdPasswordPatch({
        path: {
            user_id: user.id!
        }
    })
    if (req.error) {
        toast.add({
            title: '문제가 발생했습니다.',
            description: `지속적으로 발생하는 경우 관리자에게 문의 바랍니다.`,
            color: "error"
        })
        return
    }

    toast.add({
        title: '정상적으로 처리되었습니다.',
        description: `'${user.name}' 사용자의 비밀번호가 초기화되었습니다.`,
        color: "success"
    })

    open.value = false
}
</script>

<template>
    <UModal
        :title="`정말로 '${user.name}' 사용자의 비밀번호를 초기화 할까요?`"
        description="비밀번호가 초기 상태로 설정되며, 로그인시 비밀번호를 지정할 수 있게됩니다."
        :close="false"
        v-model:open="open"
        :ui="{ footer: 'justify-end' }"
        :dismissible="!loading"
    >
        <template #footer>
            <UButton label="초기화" color="error" variant="outline" class="cursor-pointer" :loading="loading" @click="resetPassword" />
            <UButton label="취소" color="neutral" class="cursor-pointer" :disabled="loading" @click="open = false" />
        </template>
    </UModal>
</template>