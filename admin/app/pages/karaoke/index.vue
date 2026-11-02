<script setup lang="ts">
import { UserPermission, KaraokeStatus, type KaraokeResponse } from '@/client'
import type { TableColumn } from '@nuxt/ui'
import { karaokeTimeLabel, karaokeStatusLabel, karaokeStatusColor, todayDateString } from '@/utils/karaoke'

import CreateModal from '@/components/karaoke/karaokeCreateModal.vue'
import DeleteModal from '@/components/karaoke/karaokeDeleteModal.vue'
import FinalBidModal from '@/components/karaoke/karaokeFinalBidModal.vue'

definePageMeta({
    permissions: [ UserPermission.MANAGE_KARAOKE ]
})

const today = todayDateString()
const filterDate = ref<string>(today)
const isPastDate = computed(() => filterDate.value < today)
const isCreateModalOpen = ref(false)
const actionsKaraoke = ref<{
    action: 'delete' | 'final-bid',
    karaoke: KaraokeResponse
} | undefined>()

const { data: karaokesResponse, pending, refresh } = await useAsyncData('karaoke.getKaraokeList', async (_nuxtApp, { signal }) => {
    const req = await $API.getKaraokeList({
        // 서버는 date 쿼리를 ISO date 문자열로 검증하므로 문자열 그대로 전달한다.
        query: { date: filterDate.value } as unknown as { date?: Date | null },
        ...signal
    })

    if (!req.data?.success) return

    return req.data
}, { watch: [ filterDate ] })

const karaokes = computed(() => karaokesResponse.value?.success ? karaokesResponse.value.data : [])

const columns = computed<TableColumn<KaraokeResponse>[]>(() => {
    const UBadge = resolveComponent('UBadge')
    const UDropdownMenu = resolveComponent('UDropdownMenu')
    const UButton = resolveComponent('UButton')

    return [
        { accessorKey: 'time', header: '시간', cell: ({ row }) => karaokeTimeLabel(row.original.time) },
        {
            accessorKey: 'status',
            header: '상태',
            cell: ({ row }) => h(UBadge, {
                color: karaokeStatusColor(row.original.status),
                variant: 'subtle'
            }, () => karaokeStatusLabel(row.original.status))
        },
        {
            accessorKey: 'start_time',
            header: '시작 시간',
            cell: ({ row }) => new Date(row.original.start_time).toLocaleString('ko-KR')
        },
        {
            accessorKey: 'end_time',
            header: '종료 시간',
            cell: ({ row }) => new Date(row.original.end_time).toLocaleString('ko-KR')
        },
        { accessorKey: 'min_point', header: '최소 입찰가', cell: ({ row }) => `${(row.original.min_point ?? 0).toLocaleString()} P` },
        {
            accessorKey: 'highest_bid',
            header: '최고 입찰가',
            cell: ({ row }) => row.original.status === KaraokeStatus.CONFIRMED
                ? '-'
                : (row.original.highest_bid != null ? `${row.original.highest_bid.toLocaleString()} P` : '-')
        },
        {
            id: 'actions',
            meta: { class: { td: 'text-right' } },
            cell: ({ row }) => h(
                UDropdownMenu,
                {
                    content: { align: 'end' },
                    items: [
                        ...(row.original.status === KaraokeStatus.CONFIRMED ? [{
                            label: '낙찰자 조회',
                            icon: 'i-lucide-trophy',
                            onSelect() {
                                actionsKaraoke.value = { action: 'final-bid', karaoke: row.original }
                            }
                        }] : []),
                        {
                            label: '경매 삭제',
                            icon: 'i-lucide-trash-2',
                            color: 'error',
                            onSelect() {
                                actionsKaraoke.value = { action: 'delete', karaoke: row.original }
                            }
                        }
                    ]
                },
                () => h(UButton, {
                    icon: 'i-lucide-ellipsis-vertical',
                    color: 'neutral',
                    variant: 'ghost',
                    ui: { base: 'cursor-pointer hover:bg-accented dark:hover:bg-elevated' }
                })
            )
        }
    ]
})
</script>

<template>
    <CreateModal
        v-if="isCreateModalOpen"
        @close="isCreateModalOpen = false"
        @create="() => { isCreateModalOpen = false; refresh(); }"
    />
    <DeleteModal
        v-if="actionsKaraoke?.action === 'delete'"
        :karaoke="actionsKaraoke.karaoke"
        @close="actionsKaraoke = undefined"
        @delete="refresh"
    />
    <FinalBidModal
        v-if="actionsKaraoke?.action === 'final-bid'"
        :karaoke="actionsKaraoke.karaoke"
        @close="actionsKaraoke = undefined"
    />

    <UDashboardPanel :ui="{
        root: 'overflow-y-auto',
        body: 'min-h-fit'
    }">
        <template #header>
            <UDashboardNavbar title="노래방 경매 관리">
                <template #leading>
                    <UDashboardSidebarCollapse />
                </template>
            </UDashboardNavbar>
        </template>

        <template #body>
            <div class="flex items-center justify-between mb-4">
                <UInput v-model="filterDate" type="date" class="w-48" />
                <UButton v-if="!isPastDate" color="primary" icon="i-lucide-plus" @click="isCreateModalOpen = true">
                    경매 생성
                </UButton>
            </div>

            <UTable
                :data="karaokes"
                :columns="columns"
                :loading="pending"
                class="w-full"
            />
        </template>
    </UDashboardPanel>
</template>
