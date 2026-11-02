<script setup lang="ts">
import { UserType, UserPermission, type User } from '@/client'
import type { TableColumn } from '@nuxt/ui'

import DeleteModal from "@/components/users/userDeleteModal.vue"
import PasswordResetModal from "@/components/users/userPasswordResetModal.vue"
import EditSlideover from "@/components/users/userEditSlideover.vue"
import PointManageModal from "@/components/users/userPointManageModal.vue"

definePageMeta({
    permissions: [ UserPermission.MANAGE_USER ]
})

const session = useSession()
const actionsUser = ref<{
    action: 'delete' | 'edit' | 'password',
    user: User
} | undefined>()
const filterUser = reactive<{
    type?: UserType
    permission?: number
}>({
    type: undefined,
    permission: undefined
})
const maxPage = ref<number>(0);
const dataPage = ref<number>(1);

const rowSelection = ref<Record<string, boolean>>({})
const search = ref('')
const searchLoading = ref<boolean>(false)
const searchUsers = ref<User[] | undefined>(undefined)
let searchTimeout: NodeJS.Timeout | null = null
const isPointManageModalOpen = ref(false)

const canGrantPoint = computed(() => ((session.value?.permissions || 0) & UserPermission._GRANT_POINT) === UserPermission._GRANT_POINT)
const canDeductPoint = computed(() => ((session.value?.permissions || 0) & UserPermission._DEDUCT_POINT) === UserPermission._DEDUCT_POINT)
const canManagePoint = computed(() => canGrantPoint.value || canDeductPoint.value)

const queryParams = computed(() => ({
    limit: 20,
    page: dataPage.value,
    user_type: filterUser.type,
    permission: filterUser.permission
}));
const { data: studentsResponse, pending, refresh } = await useAsyncData('users.getUsersAdminUsersGet', async (_nuxtApp, { signal }) => {
    const req = await $API.getUsersAdminUsersGet({
        query: queryParams.value,
        ...signal
    })

    if (!req.data?.success || req.response == undefined) return;
    maxPage.value = Number(req.response.headers.get("X-MAX-PAGE"));

    return req.data;
}, { watch: [ queryParams ] })

const students = computed(() => {
    if (searchUsers.value != undefined) {
        return searchUsers.value
    }
    if (studentsResponse.value?.success) {
        return studentsResponse.value.data
    }
    return []
})

const columns = computed<TableColumn<User>[]>(() => {
    const UCheckbox = resolveComponent('UCheckbox')
    const UDropdownMenu = resolveComponent('UDropdownMenu')
    const UButton = resolveComponent('UButton')

    const cols: TableColumn<User>[] = [
        {
            id: 'select',
            header: ({ table }) => h(UCheckbox, {
                modelValue: table.getIsAllPageRowsSelected(),
                indeterminate: table.getIsSomePageRowsSelected(),
                'onUpdate:modelValue': (value: boolean) => table.toggleAllPageRowsSelected(value),
                ui: {
                    base: "cursor-pointer"
                }
            }),
            cell: ({ row }) => h(UCheckbox, {
                modelValue: row.getIsSelected(),
                'onUpdate:modelValue': (value: boolean) => row.toggleSelected(value),
                ui: {
                    base: "cursor-pointer"
                }
            })
        },
        { accessorKey: 'id', header: '고유번호' },
        { accessorKey: 'name', header: '이름' },
        { accessorKey: 'type', header: '구분' },
        { accessorKey: 'grade', header: '학년' },
        { accessorKey: 'number', header: '반' },
        { accessorKey: 'point', header: '현재 포인트' },
        { accessorKey: 'total_point', header: '누적 포인트' },
        {
            id: 'actions',
            meta: {
                class: {
                    td: 'text-right'
                }
            },
            cell: ({ row }) => {
                return h(
                    UDropdownMenu,
                    {
                        content: {
                            align: 'end'
                        },
                        items: [
                            {
                                label: '사용자 삭제',
                                onSelect() {
                                    actionsUser.value = {
                                        action: "delete",
                                        user: row.original
                                    }
                                },
                                disabled: row.original.id == session.value!.id,
                                icon: 'i-lucide-trash-2',
                                color: "error"
                            },
                            {
                                label: '사용자 수정',
                                onSelect() {
                                    actionsUser.value = {
                                        action: "edit",
                                        user: row.original
                                    }
                                },
                                disabled: row.original.id == session.value!.id,
                                icon: 'i-lucide-file-pen-line'
                            },
                            {
                                label: '비밀번호 초기화',
                                onSelect() {
                                    actionsUser.value = {
                                        action: "password",
                                        user: row.original
                                    }
                                },
                                icon: 'i-lucide-key-round'
                            }
                        ]
                    },
                    () =>
                        h(UButton, {
                            icon: 'i-lucide-ellipsis-vertical',
                            color: 'neutral',
                            variant: 'ghost',
                            ui: {
                                base: 'cursor-pointer hover:bg-accented dark:hover:bg-elevated'
                            }
                        })
                )
            }
        }
    ]

    return cols
})

const selectedIds = computed(() => Object.keys(rowSelection.value).filter(key => rowSelection.value[key]))

const onSearch = async (event: InputEvent) => {
    search.value = (event.target as HTMLInputElement).value;

    searchUsers.value = []

    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
        if (search.value.replaceAll(" ", "").length <= 0) {
            searchUsers.value = undefined
            return
        }

        searchLoading.value = true
        const search_req = await $API.searchSearchGet({
            query: {
                q: search.value
            }
        })
        if (!search_req.data?.success || search_req.response == undefined) return;
        searchUsers.value = search_req.data.data
        searchLoading.value = false
    }, 200);
}
</script>

<template>
    <DeleteModal
        v-if="actionsUser?.action == 'delete'"
        :user="actionsUser!.user"
        @close="actionsUser = undefined"
        @delete="refresh"
    />
    <PasswordResetModal
        v-if="actionsUser?.action == 'password'"
        :user="actionsUser!.user"
        @close="actionsUser = undefined"
    />
    <EditSlideover
        v-if="actionsUser?.action == 'edit'"
        :user="actionsUser!.user"
        @close="actionsUser = undefined"
        @edit="refresh"
    />
    <PointManageModal
        v-if="isPointManageModalOpen"
        :users="selectedIds"
        @close="isPointManageModalOpen = false"
        @success="() => { isPointManageModalOpen = false; refresh(); rowSelection = {}; }"
    />

    <UDashboardPanel :ui="{
        root: 'overflow-y-auto',
        body: 'min-h-fit'
    }">
        <template #header>
            <UDashboardNavbar title="학생 관리">
                <template #leading>
                    <UDashboardSidebarCollapse />
                </template>
            </UDashboardNavbar>
        </template>

        <template #body>
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-2">
                    <UInput v-model="search" @input="onSearch" icon="i-lucide-search" placeholder="이름 또는 학번 검색..." class="w-64" />
                    <UButton 
                        v-if="selectedIds.length > 0 && canManagePoint"
                        color="primary" 
                        variant="solid" 
                        icon="i-lucide-coins"
                        @click="isPointManageModalOpen = true"
                    >
                        포인트 관리 ({{ selectedIds.length }}명)
                    </UButton>
                </div>
            </div>

            <UTable 
                v-model:row-selection="rowSelection" 
                :get-row-id="(row) => String(row.id)"
                :data="students"
                :columns="columns"
                :loading="pending || searchLoading"
                class="w-full"
            >
                <template #type-cell="{ row }">
                    <UBadge :color="row.original.type === 'student' ? 'success' : 'neutral'" variant="subtle">
                        {{ row.original.type === 'student' ? '학생' : (row.original.type === 'teacher' ? '교사' : '서비스') }}
                    </UBadge>
                </template>
                <template #point-cell="{ row }">
                    <span class="font-semibold text-primary">{{ row.original.point?.toLocaleString() || 0 }} P</span>
                </template>
                <template #total_point-cell="{ row }">
                    <span class="text-gray-500">{{ row.original.total_point?.toLocaleString() || 0 }} P</span>
                </template>
            </UTable>
            <UPagination v-model:page="dataPage" :total="maxPage" :items-per-page="1" v-if="searchUsers == undefined" />

        </template>
    </UDashboardPanel>
</template>
