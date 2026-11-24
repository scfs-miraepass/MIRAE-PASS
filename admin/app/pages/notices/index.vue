<script setup lang="ts">
import { UserPermission } from "@miraepass/api-client";
import type { TableColumn } from "@nuxt/ui";
import { NOTICE_MANAGEMENT_PERMISSIONS } from "~/utils/permission.ts";
import { NOTICE_CONTENT_KIND, noticeDateLabel, toManagedNotices, type ManagedNotice } from "~/utils/notice";

import FormModal from "~/components/notices/noticeFormModal.vue";
import DeleteModal from "~/components/notices/noticeDeleteModal.vue";

definePageMeta({ permissions: NOTICE_MANAGEMENT_PERMISSIONS });

// 한 페이지에 보여줄 공지 개수
const NOTICE_PAGE_SIZE = 20;

const session = useSession();
const canCreate = computed(() => hasPermission(session.value?.permissions, UserPermission.CREATE_POST));
const canManage = computed(() => hasPermission(session.value?.permissions, UserPermission.MANAGE_POST));
const canEdit = (notice: ManagedNotice) => canManage.value || notice.authorId === session.value?.id;

const page = ref(1);
const action = ref<{ type: "create" } | { type: "edit" | "delete"; notice: ManagedNotice } | undefined>();

const { data, pending, error, refresh } = useAsyncData(
    "notices.management",
    async (_nuxtApp, { signal }) => {
        const req = await $API.getPostsPostsGet({
            query: { content_kind: NOTICE_CONTENT_KIND, page: page.value, size: NOTICE_PAGE_SIZE },
            signal,
        });
        if (req.error) {
            throw createError({
                statusCode: req.response?.status ?? 503,
                statusMessage: req.response?.status === 403
                    ? "공지 목록을 볼 수 있는 권한이 없습니다."
                    : "공지 목록을 불러오지 못했습니다.",
            });
        }
        return {
            notices: toManagedNotices(req.data.data ?? []),
            maxPage: Number(req.response?.headers.get("X-MAX-PAGE")) || 1,
        };
    },
    { server: false, watch: [page] },
);

const notices = computed(() => data.value?.notices ?? []);

const columns: TableColumn<ManagedNotice>[] = [
    { accessorKey: "title", header: "공지", meta: { class: { td: "w-full max-w-0" } } },
    { accessorKey: "createdAt", header: "작성일", meta: { class: { td: "whitespace-nowrap text-muted" } } },
    { accessorKey: "updatedAt", header: "마지막 수정", meta: { class: { td: "whitespace-nowrap text-muted" } } },
    { id: "actions", meta: { class: { td: "text-right" } } },
];

const actionItems = (notice: ManagedNotice) => [
    { label: "수정", icon: "i-lucide-pencil", onSelect: () => (action.value = { type: "edit", notice }) },
    { label: "삭제", icon: "i-lucide-trash-2", color: "error" as const, onSelect: () => (action.value = { type: "delete", notice }) },
];

async function onCreated() {
    action.value = undefined;
    // 새 공지는 첫 페이지 맨 위에 추가되므로 첫 페이지로 이동한다.
    if (page.value > 1) page.value = 1;
    else await refresh();
}

async function onDeleted() {
    action.value = undefined;
    // 마지막 페이지의 마지막 공지를 지운 경우 이전 페이지로 이동한다.
    if (page.value > 1 && notices.value.length === 1) page.value--;
    else await refresh();
}
</script>

<template>
    <FormModal v-if="action?.type === 'create'" @close="action = undefined" @success="onCreated" />
    <FormModal
        v-if="action?.type === 'edit'"
        :notice="action.notice"
        @close="action = undefined"
        @success="() => { action = undefined; refresh(); }"
    />
    <DeleteModal v-if="action?.type === 'delete'" :notice="action.notice" @close="action = undefined" @success="onDeleted" />

    <UDashboardPanel id="notices" :ui="{ root: 'overflow-y-auto', body: 'min-h-fit' }">
        <template #header>
            <UDashboardNavbar title="공지사항">
                <template #leading><UDashboardSidebarCollapse /></template>
                <template #right>
                    <UButton v-if="canCreate" icon="i-lucide-plus" class="cursor-pointer" @click="action = { type: 'create' }">
                        공지 작성
                    </UButton>
                </template>
            </UDashboardNavbar>
        </template>

        <template #body>
            <UAlert
                v-if="error"
                color="error"
                variant="subtle"
                icon="i-lucide-circle-alert"
                :title="error.statusMessage"
                :actions="error.statusCode === 403 ? [] : [{ label: '다시 시도', color: 'error', variant: 'outline', onClick: () => refresh() }]"
            />

            <UTable
                v-else
                :data="notices"
                :columns="columns"
                :loading="pending"
                class="w-full rounded-lg border border-default"
            >
                <template #title-cell="{ row }">
                    <p class="truncate font-medium text-highlighted">{{ row.original.title }}</p>
                    <p class="mt-0.5 truncate text-muted">{{ row.original.text }}</p>
                </template>
                <template #createdAt-cell="{ row }">{{ noticeDateLabel(row.original.createdAt) }}</template>
                <template #updatedAt-cell="{ row }">{{ noticeDateLabel(row.original.updatedAt) }}</template>
                <template #actions-cell="{ row }">
                    <UDropdownMenu v-if="canEdit(row.original)" :items="actionItems(row.original)" :content="{ align: 'end' }">
                        <UButton
                            icon="i-lucide-ellipsis-vertical"
                            color="neutral"
                            variant="ghost"
                            aria-label="공지 메뉴"
                            :ui="{ base: 'cursor-pointer hover:bg-accented dark:hover:bg-elevated' }"
                        />
                    </UDropdownMenu>
                </template>
                <template #empty>
                    <div class="flex flex-col items-center gap-2 py-10 text-muted">
                        <UIcon name="i-lucide-megaphone" class="size-8" />
                        <p>게시된 공지가 없습니다.</p>
                        <UButton v-if="canCreate" variant="soft" icon="i-lucide-plus" class="mt-1 cursor-pointer" @click="action = { type: 'create' }">
                            첫 공지 작성하기
                        </UButton>
                    </div>
                </template>
            </UTable>

            <UPagination
                v-if="data && data.maxPage > 1"
                v-model:page="page"
                :total="data.maxPage"
                :items-per-page="1"
                :disabled="pending"
                class="mt-4"
            />
        </template>
    </UDashboardPanel>
</template>
