<script setup lang="ts">
import type { User } from '@/client'

const { user } = defineProps<{
    user: User
}>()
const open = ref<boolean>(true);
const loading = ref<boolean>(false);
const emit = defineEmits(['close', 'delete'])
const toast = useToast()

watch(open, value => {
    if (!value) {
        setTimeout(() => emit('close'), 200)
    }
})

const userDelete = async () => {
    loading.value = true
    const req = await $API.deleteUserAdminUsersUserIdDelete({
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
        description: `'${user.name}' 사용자가 삭제되었습니다.`,
        color: "success"
    })

    open.value = false
    emit('delete')
}
</script>

<template>
    <UModal
        :title="`정말로 '${user.name}' 사용자를 삭제 하시겠습니까?`"
        description="해당 사용자의 모든 데이터가 삭제됩니다. 삭제 후에는 되돌릴 수 없습니다."
        :close="false"
        v-model:open="open"
        :ui="{ footer: 'justify-end' }"
        :dismissible="!loading"
    >
        <template #footer>
            <UButton label="삭제" color="error" variant="outline" class="cursor-pointer" :loading="loading" @click="userDelete" />
            <UButton label="취소" color="neutral" class="cursor-pointer" :disabled="loading" @click="open = false" />
        </template>
    </UModal>
</template>