<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { UserPermission, type User } from '@/client'

const { user } = defineProps<{
    user: User
}>()

const open = ref<boolean>(true);
const loading = ref<boolean>(false);
const confirmCloseOpen = ref<boolean>(false);
const emit = defineEmits(['close', 'edit'])
const toast = useToast()

const isDirty = computed(() => {
    return form.value.name !== user.name ||
        form.value.permissions !== (user.permissions || 0)
})

const onOpenChange = (value: boolean) => {
    if (!value && isDirty.value) {
        confirmCloseOpen.value = true
        return
    }
    open.value = value
}

const forceClose = () => {
    confirmCloseOpen.value = false
    open.value = false
}

const form = ref({
    name: user.name,
    permissions: user.permissions || 0
})

const permissionList = [
    { label: '유저 검색', value: UserPermission.SEARCH_USER, description: '다른 유저의 정보를 검색하고 조회할 수 있는 권한' },
    { label: '포인트 차감(결제)', value: UserPermission._DEDUCT_POINT, description: '유저의 보유 포인트를 차감할 수 있는 권한' },
    { label: '포인트 지급', value: UserPermission._GRANT_POINT, description: '유저에게 포인트를 지급할 수 있는 권한' },
    { label: '포인트 무제한', value: UserPermission.NO_LIMIT_POINT, description: '포인트 지급/차감 시 시스템 한도 제한을 받지 않는 권한' },
    { label: '퀘스트 생성', value: UserPermission.CREATE_QUEST, description: '새로운 퀘스트를 생성할 수 있는 권한' },
    { label: '퀘스트 관리', value: UserPermission.MANAGE_QUEST, description: '퀘스트 정보를 수정, 삭제 등 전반적으로 관리할 수 있는 권한' },
    { label: '스탬프 지급', value: UserPermission._GIVE_STAMP, description: '유저에게 스탬프를 부여할 수 있는 권한' },
    { label: '랭킹 보기', value: UserPermission.VIEW_RANK, description: '전체 유저의 포인트 랭킹 순위를 열람할 수 있는 권한' },
    { label: '포인트 보기', value: UserPermission.VIEW_POINT, description: '자신의 현재 보유 포인트를 열람할 수 있는 권한' },
    { label: '포인트 내역 보기', value: UserPermission.VIEW_POINT_HISTORY, description: '자신의 포인트 변동(지급/차감) 내역을 열람할 수 있는 권한' },
    { label: '게시글 관리', value: UserPermission.MANAGE_POST, description: '게시판의 모든 게시물과 댓글을 수정, 삭제 등 관리할 수 있는 권한' },
    { label: '게시글 작성', value: UserPermission.CREATE_POST, description: '게시판에 새로운 게시물을 작성할 수 있는 권한' },
    { label: '다른 유저 포인트 보기', value: UserPermission._VIEW_USER_POINT, description: '다른 유저가 보유한 포인트를 열람할 수 있는 권한' },
    { label: '퀘스트 참여', value: UserPermission.JOIN_QUEST, description: '진행 중인 퀘스트에 참여할 수 있는 권한' },
    { label: '유저 관리', value: UserPermission._MANAGE_USER, description: '다른 유저의 정보 및 권한 등을 전반적으로 관리할 수 있는 권한' },
    { label: '게시글 보기', value: UserPermission.VIEW_POST, description: '게시판의 게시물을 읽을 수 있는 권한' },
    { label: '스탬프 보기', value: UserPermission.VIEW_STAMP, description: '보유한 스탬프 목록을 열람할 수 있는 권한' },
    { label: '퀘스트 보기', value: UserPermission.VIEW_QUEST, description: '진행 중인 퀘스트 목록을 열람할 수 있는 권한' },
    { label: '노래방 참여', value: UserPermission.JOIN_KARAOKE, description: '노래방 예약에 참여(입찰)할 수 있는 권한' },
    { label: '노래방 관리', value: UserPermission.MANAGE_KARAOKE, description: '노래방 예약을 생성, 삭제, 최종 낙찰 처리 등 전반적으로 관리할 수 있는 권한' },
    { label: '노래방 보기', value: UserPermission.VIEW_KARAOKE, description: '노래방 예약 목록을 열람할 수 있는 권한' },
]

const presetPermissions = [
    { label: '학생 (기본)', value: UserPermission.STUDENT },
    { label: '교사 (기본)', value: UserPermission.TEACHER },
    { label: '관리자 (기본)', value: UserPermission.ADMIN | UserPermission.TEACHER },
    { label: '권한 없음', value: UserPermission.NONE }
]

const applyPreset = (presetValue: number) => {
    form.value.permissions = presetValue
}

watch(open, value => {
    if (!value) {
        setTimeout(() => emit('close'), 200)
    }
})

const onSubmit = async () => {
    loading.value = true
    const req = await $API.updateUserAdminUsersUserIdPatch({
        path: {
            user_id: user.id!
        },
        body: form.value
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
        description: `'${user.name}' 사용자가 수정되었습니다.`,
        color: 'success'
    })

    open.value = false
    emit('edit')
}
</script>

<template>
    <USlideover
        :title="`${user.name} 사용자 수정`"
        description="사용자 정보를 수정합니다."
        :open="open"
        @update:open="onOpenChange"
        :close="false"
        :dismissible="!loading"
    >
        <template #body>
            <form @submit.prevent="onSubmit" class="space-y-4">
                <UFormField label="이름" name="name">
                    <UInput v-model="form.name" />
                </UFormField>
                
                <div class="pt-4 border-t border-gray-200 dark:border-gray-800">
                    <div class="flex items-center justify-between mb-2">
                        <h3 class="text-sm font-medium">권한 설정</h3>
                        <div class="flex gap-2">
                            <UButton 
                                v-for="preset in presetPermissions" 
                                :key="preset.label"
                                :label="preset.label"
                                size="xs"
                                variant="soft"
                                color="neutral"
                                @click="applyPreset(preset.value)"
                            />
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-3 mt-4">
                        <UTooltip 
                            v-for="perm in permissionList"
                            :key="perm.value"
                            :text="perm.description"
                            :delay-duration="0"
                            :content="{
                                side: 'left'
                            }"
                            arrow
                        >
                            <div>
                                <UCheckbox
                                    :label="perm.label"
                                    :model-value="(form.permissions & perm.value) === perm.value"
                                    @update:model-value="(checked: boolean | 'indeterminate') => {
                                        if (typeof checked != 'boolean') return
                                        if (checked) form.permissions |= perm.value
                                        else form.permissions &= ~perm.value
                                    }"
                                    :ui="{
                                        root: 'cursor-pointer',
                                        base: 'cursor-pointer',
                                        label: 'cursor-pointer'
                                    }"
                                />
                            </div>
                        </UTooltip>
                    </div>
                </div>
            </form>
        </template>
        <template #footer>
            <div class="flex justify-end gap-2 w-full">
                <UButton label="취소" color="neutral" variant="ghost" class="cursor-pointer" :disabled="loading" @click="onOpenChange(false)" />
                <UButton label="저장" color="primary" class="cursor-pointer" :loading="loading" @click="onSubmit" :disabled="!isDirty" />
            </div>
        </template>
    </USlideover>

    <UModal
        title="수정 취소"
        description="저장하지 않은 변경사항이 있습니다. 정말로 취소하시겠습니까?"
        v-model:open="confirmCloseOpen"
        :close="false"
    >
        <template #footer>
            <div class="flex justify-end gap-2 w-full">
                <UButton label="나가기" color="error" variant="outline" class="cursor-pointer" @click="forceClose" />
                <UButton label="계속 수정" color="neutral" class="cursor-pointer" @click="confirmCloseOpen = false" />
            </div>
        </template>
    </UModal>
</template>
