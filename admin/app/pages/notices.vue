<script setup lang="ts">
import { UserPermission } from '@miraepass/api-client'

interface ManagedNotice {
    id: number
    title: string
    text: string
    can_edit: boolean
}

const session = useSession()
const canCreate = computed(() => hasPermission(session.value?.permissions, UserPermission.CREATE_POST))
const title = ref('')
const body = ref('')
const editing = ref<ManagedNotice | null>(null)
const editTitle = ref('')
const editBody = ref('')
const deleting = ref<ManagedNotice | null>(null)
const busy = ref(false)
const toast = useToast()
const notices = ref<ManagedNotice[]>([])
const loading = ref(true)
const listError = ref('')

async function refresh() {
    loading.value = true
    listError.value = ''
    try {
        const response = await fetch('/api/posts/notices/manage', { cache: 'no-store' })
        if (response.status === 403) {
            listError.value = '공지 목록을 볼 수 있는 권한이 없습니다.'
            return
        }
        if (!response.ok) throw new Error('List request failed')
        const result = await response.json() as { data: ManagedNotice[] }
        if (!Array.isArray(result.data)) throw new Error('Invalid notice list')
        notices.value = result.data
    } catch {
        listError.value = '공지 목록을 불러오지 못했습니다.'
    } finally {
        loading.value = false
    }
}

onMounted(refresh)

function startEdit(notice: ManagedNotice) {
    editing.value = notice
    editTitle.value = notice.title
    editBody.value = notice.text
}

async function saveNotice(current: ManagedNotice | null) {
    const noticeTitle = (current ? editTitle.value : title.value).trim()
    const text = (current ? editBody.value : body.value).trim()
    if (busy.value || !noticeTitle || !text || (!current && !canCreate.value)) return
    busy.value = true
    try {
        const requestBody = { title: noticeTitle, content_data: { kind: 'notice', text } }
        const result = current
            ? await $API.updatePostPostsPostIdPatch({ path: { post_id: current.id }, body: requestBody })
            : await $API.createPostPostsPost({ body: requestBody })
        if (!result.data?.success) throw new Error('Save failed')
        if (current) {
            editing.value = null
        } else {
            title.value = ''
            body.value = ''
        }
        toast.add({ title: current ? '공지를 수정했습니다.' : '공지를 게시했습니다.', color: 'success' })
        await refresh()
    } catch {
        toast.add({ title: current ? '공지를 수정하지 못했습니다.' : '공지를 게시하지 못했습니다.', color: 'error' })
    } finally {
        busy.value = false
    }
}

async function deleteNotice() {
    const notice = deleting.value
    if (busy.value || !notice) return
    busy.value = true
    try {
        const result = await $API.deletePostPostsPostIdDelete({ path: { post_id: notice.id } })
        if (result.response?.status !== 204) throw new Error('Delete failed')
        deleting.value = null
        toast.add({ title: '공지를 삭제했습니다.', color: 'success' })
        await refresh()
    } catch {
        toast.add({ title: '공지를 삭제하지 못했습니다. 다시 시도해 주세요.', color: 'error' })
    } finally {
        busy.value = false
    }
}
</script>

<template>
    <UDashboardPanel id="notices">
        <template #header>
            <UDashboardNavbar title="공지사항">
                <template #leading><UDashboardSidebarCollapse /></template>
            </UDashboardNavbar>
        </template>
        <template #body>
            <form v-if="canCreate" class="max-w-xl space-y-4" @submit.prevent="saveNotice(null)">
                <h2 class="text-lg font-semibold">새 공지</h2>
                <UFormField label="제목" required>
                    <UInput v-model="title" class="w-full" maxlength="100" required :disabled="busy" />
                </UFormField>
                <UFormField label="내용" required>
                    <UTextarea v-model="body" class="w-full" :rows="6" maxlength="2000" required :disabled="busy" />
                </UFormField>
                <UButton type="submit" :loading="busy && !editing && !deleting" :disabled="busy || !title.trim() || !body.trim()">게시하기</UButton>
            </form>
            <section class="mt-6 max-w-3xl space-y-3" aria-labelledby="notice-list-heading">
                <h2 id="notice-list-heading" class="text-lg font-semibold">게시된 공지</h2>
                <div v-if="listError" role="alert">
                    <p>{{ listError }}</p>
                    <UButton class="mt-2" variant="outline" @click="refresh()">다시 시도</UButton>
                </div>
                <p v-else-if="loading && !notices.length" role="status">공지 목록을 불러오는 중입니다.</p>
                <p v-else-if="!notices.length">게시된 공지가 없습니다.</p>
                <ul v-else class="divide-y divide-default rounded-lg border border-default">
                    <li v-for="notice in notices" :key="notice.id" class="p-4">
                        <form v-if="editing?.id === notice.id" class="space-y-3" @submit.prevent="saveNotice(notice)">
                            <UFormField label="제목" required>
                                <UInput v-model="editTitle" class="w-full" maxlength="100" required :disabled="busy" />
                            </UFormField>
                            <UFormField label="내용" required>
                                <UTextarea v-model="editBody" class="w-full" :rows="6" maxlength="2000" required :disabled="busy" />
                            </UFormField>
                            <div class="flex gap-2">
                                <UButton type="submit" :loading="busy" :disabled="!editTitle.trim() || !editBody.trim()">저장</UButton>
                                <UButton color="neutral" variant="outline" :disabled="busy" @click="editing = null">취소</UButton>
                            </div>
                        </form>
                        <template v-else>
                            <div class="flex flex-wrap items-start justify-between gap-2">
                                <h3 class="min-w-0 break-words font-medium">{{ notice.title }}</h3>
                                <div v-if="notice.can_edit" class="flex gap-2">
                                    <UButton color="neutral" variant="outline" :disabled="busy || !!editing || !!deleting" @click="startEdit(notice)">수정</UButton>
                                    <UButton color="error" variant="outline" :disabled="busy || !!editing || !!deleting" @click="deleting = notice">삭제</UButton>
                                </div>
                            </div>
                            <p class="mt-2 whitespace-pre-wrap break-words text-sm text-muted">{{ notice.text }}</p>
                            <div v-if="deleting?.id === notice.id" class="mt-3 space-y-2 rounded-md border border-error/40 p-3">
                                <p class="break-words">‘{{ notice.title }}’ 공지를 삭제할까요?</p>
                                <div class="flex gap-2">
                                    <UButton color="error" :loading="busy" @click="deleteNotice">삭제 확인</UButton>
                                    <UButton color="neutral" variant="outline" :disabled="busy" @click="deleting = null">취소</UButton>
                                </div>
                            </div>
                        </template>
                    </li>
                </ul>
            </section>
        </template>
    </UDashboardPanel>
</template>
