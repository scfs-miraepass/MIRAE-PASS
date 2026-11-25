<script setup lang="ts">
import { UserPermission, type User, type StickerBalance, type StickerHistoryItem } from "@miraepass/api-client";
import type { TableColumn } from "@nuxt/ui";

import StickerManageModal from "@/components/stickers/stickerManageModal.vue";
import StickerResetModal from "@/components/stickers/stickerResetModal.vue";
import StickerHistoryCancelModal from "@/components/stickers/stickerHistoryCancelModal.vue";

definePageMeta({
    permissions: [ UserPermission.MANAGE_STICKER ],
});

const PAGE_SIZE = 20;

const toast = useToast();

// 유저 검색 / 선택
const search = ref<string>("");
const searchLoading = ref<boolean>(false);
const searchUsers = ref<User[]>([]);
let searchTimeout: ReturnType<typeof setTimeout> | undefined;

const selectedUser = ref<User | undefined>();
const balance = ref<StickerBalance | undefined>();
const balanceLoading = ref<boolean>(false);

const onSearch = (event: InputEvent) => {
    search.value = (event.target as HTMLInputElement).value;

    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
        if (search.value.replaceAll(" ", "").length <= 0) {
            searchUsers.value = [];
            return;
        }

        searchLoading.value = true;
        const req = await $API.searchSearchGet({
            query: { q: search.value, t: ["student", "teacher"] },
        });
        searchLoading.value = false;
        if (req.error) {
            toast.add({ title: "검색 실패", description: stickerErrorMessage(req.error), color: "error" });
            return;
        }
        searchUsers.value = req.data.data;
    }, 200);
};

onBeforeUnmount(() => {
    if (searchTimeout) clearTimeout(searchTimeout);
});

const loadBalance = async () => {
    if (!selectedUser.value) {
        balance.value = undefined;
        return;
    }
    balanceLoading.value = true;
    const req = await $API.getUserStickerBalance({ path: { user_id: selectedUser.value.id! } });
    balanceLoading.value = false;
    if (req.error) {
        balance.value = undefined;
        toast.add({ title: "보유 수 조회 실패", description: stickerErrorMessage(req.error), color: "error" });
        return;
    }
    balance.value = req.data.data;
};

const selectUser = async (user: User) => {
    selectedUser.value = user;
    searchUsers.value = [];
    search.value = "";
    dataPage.value = 1;
    await loadBalance();
};

const clearUser = () => {
    selectedUser.value = undefined;
    balance.value = undefined;
    dataPage.value = 1;
};

// 지급 한도는 보유 수가 아니라 이번 주에 받은 수 기준
const remaining = computed(() => (balance.value ? Math.max(0, balance.value.max - balance.value.week_count) : 0));

// 모달
const manageMode = ref<"grant" | "revoke" | undefined>();
const isResetModalOpen = ref<boolean>(false);
const cancelTarget = ref<StickerHistoryItem | undefined>();

// 기록
const maxPage = ref<number>(0);
const dataPage = ref<number>(1);

const queryParams = computed(() => ({
    limit: PAGE_SIZE,
    offset: (dataPage.value - 1) * PAGE_SIZE,
    user_id: selectedUser.value?.id ?? undefined,
}));

const { data: historyPage, pending, refresh } = await useAsyncData(
    "sticker.history",
    async (_nuxtApp, { signal }) => {
        const req = await $API.getStickerHistory({
            query: queryParams.value,
            signal,
        });
        if (req.error || !req.response) return null;

        maxPage.value = Number(req.response.headers.get("X-MAX-PAGE"));
        return req.data.data;
    },
    { watch: [ queryParams ] },
);

const history = computed<StickerHistoryItem[]>(() => historyPage.value?.items ?? []);
const periodStart = computed(() => historyPage.value?.period_start);

const formatDate = (value: Date | string | undefined) =>
    value ? new Date(value).toLocaleString("ko-KR", { dateStyle: "medium", timeStyle: "short" }) : "-";

const columns = computed<TableColumn<StickerHistoryItem>[]>(() => {
    const UDropdownMenu = resolveComponent("UDropdownMenu");
    const UButton = resolveComponent("UButton");

    return [
        { accessorKey: "created_at", header: "일시" },
        { accessorKey: "user_id", header: "대상" },
        { accessorKey: "amount", header: "수량" },
        { accessorKey: "actor_id", header: "처리자" },
        { accessorKey: "memo", header: "메모" },
        {
            id: "actions",
            meta: { class: { td: "text-right" } },
            cell: ({ row }) => h(
                UDropdownMenu,
                {
                    content: { align: "end" },
                    items: [
                        {
                            label: "기록 취소",
                            icon: "i-lucide-undo-2",
                            color: "error",
                            onSelect() {
                                cancelTarget.value = row.original;
                            },
                        },
                    ],
                },
                () => h(UButton, {
                    icon: "i-lucide-ellipsis-vertical",
                    color: "neutral",
                    variant: "ghost",
                    ui: {
                        base: "cursor-pointer hover:bg-accented dark:hover:bg-elevated",
                    },
                }),
            ),
        },
    ];
});

const onChanged = async () => {
    manageMode.value = undefined;
    await Promise.all([loadBalance(), refresh()]);
};

const onCancelled = async () => {
    cancelTarget.value = undefined;
    await Promise.all([loadBalance(), refresh()]);
};

const onReset = async () => {
    isResetModalOpen.value = false;
    dataPage.value = 1;
    await Promise.all([loadBalance(), refresh()]);
};
</script>

<template>
    <StickerManageModal
        v-if="manageMode && selectedUser && balance"
        :user="selectedUser"
        :mode="manageMode"
        :balance="balance"
        @close="manageMode = undefined"
        @success="onChanged"
    />
    <StickerResetModal
        v-if="isResetModalOpen"
        @close="isResetModalOpen = false"
        @success="onReset"
    />
    <StickerHistoryCancelModal
        v-if="cancelTarget"
        :item="cancelTarget"
        @close="cancelTarget = undefined"
        @success="onCancelled"
    />

    <UDashboardPanel :ui="{
        root: 'overflow-y-auto',
        body: 'min-h-fit'
    }">
        <template #header>
            <UDashboardNavbar title="스티커 관리">
                <template #leading>
                    <UDashboardSidebarCollapse />
                </template>
            </UDashboardNavbar>
        </template>

        <template #body>
            <!-- 기간 -->
            <p class="text-base mb-4">
                <span class="text-muted">현재 집계 기간 시작:</span>
                <span class="font-semibold ml-1">{{ formatDate(periodStart) }}</span>
                <span class="text-muted ml-2">· 매월 1일 00:00에 자동 초기화됩니다. · 한 주(월요일 00:00~)에 1인당 최대 3개까지 받을 수 있습니다.</span>
            </p>

            <!-- 학생 검색 / 선택 -->
            <div class="flex flex-col gap-3 mb-5">
                <div class="flex items-center justify-between">
                    <div class="relative w-[28rem] max-w-full">
                        <UInput
                            :model-value="search"
                            @input="onSearch"
                            icon="i-lucide-search"
                            placeholder="학생 이름 또는 학번 검색..."
                            class="w-full"
                            size="lg"
                            :loading="searchLoading"
                        />
                        <div
                            v-if="searchUsers.length > 0"
                            class="absolute z-20 mt-1 w-full rounded-md border border-default bg-default shadow-lg max-h-72 overflow-y-auto"
                        >
                            <button
                                v-for="u in searchUsers"
                                :key="u.id!"
                                type="button"
                                class="w-full text-left px-3 py-2 text-sm hover:bg-elevated flex items-center justify-between"
                                @click="selectUser(u)"
                            >
                                <span>
                                    {{ u.name }}
                                    <UBadge v-if="u.type === 'teacher'" color="neutral" variant="subtle" size="sm" class="ml-1">교사</UBadge>
                                </span>
                                <span class="text-muted">{{ u.id }}<template v-if="u.grade != null"> · {{ u.grade }}학년 {{ u.number }}반</template></span>
                            </button>
                        </div>
                    </div>
                    <UButton
                        color="error"
                        variant="outline"
                        icon="i-lucide-rotate-ccw"
                        size="lg"
                        @click="isResetModalOpen = true"
                    >
                        수동 초기화
                    </UButton>
                </div>

                <UCard v-if="selectedUser" class="w-fit min-w-80">
                    <div class="flex items-center justify-between gap-8">
                        <div>
                            <p class="font-semibold">
                                {{ selectedUser.name }}
                                <UBadge v-if="selectedUser.type === 'teacher'" color="neutral" variant="subtle" size="sm" class="ml-1">교사</UBadge>
                                <span class="text-muted font-normal text-sm ml-1">
                                    {{ selectedUser.id }}<template v-if="selectedUser.grade != null"> · {{ selectedUser.grade }}학년 {{ selectedUser.number }}반</template>
                                </span>
                            </p>
                            <p class="text-2xl font-bold mt-1">
                                <template v-if="balanceLoading">...</template>
                                <template v-else-if="balance">
                                    <UIcon name="i-lucide-heart" class="inline-block align-[-2px]" /> {{ balance.count }}
                                    <span class="text-base text-muted font-normal">· 이번 주 {{ balance.week_count }} / {{ balance.max }}</span>
                                </template>
                                <template v-else>-</template>
                            </p>
                        </div>
                        <div class="flex items-center gap-2">
                            <UButton
                                color="success"
                                icon="i-lucide-plus"
                                :disabled="!balance || remaining <= 0"
                                @click="manageMode = 'grant'"
                            >
                                지급
                            </UButton>
                            <UButton
                                color="error"
                                variant="soft"
                                icon="i-lucide-minus"
                                :disabled="!balance || balance.count <= 0"
                                @click="manageMode = 'revoke'"
                            >
                                회수
                            </UButton>
                            <UButton
                                color="neutral"
                                variant="ghost"
                                icon="i-lucide-x"
                                @click="clearUser"
                            />
                        </div>
                    </div>
                </UCard>
            </div>

            <!-- 기록 -->
            <p class="text-base font-semibold mb-2">
                {{ selectedUser ? `${selectedUser.name} ${selectedUser.type === 'teacher' ? '선생님' : '학생'}의 기록` : '이번 기간 전체 기록' }}
            </p>
            <UTable
                :data="history"
                :columns="columns"
                :loading="pending"
                class="w-full"
            >
                <template #created_at-cell="{ row }">
                    <span class="text-muted">{{ formatDate(row.original.created_at) }}</span>
                </template>
                <template #user_id-cell="{ row }">
                    <span class="font-medium">{{ row.original.user?.name ?? '-' }}</span>
                    <UBadge v-if="row.original.user?.type === 'teacher'" color="neutral" variant="subtle" size="sm" class="ml-1">교사</UBadge>
                    <span class="text-muted ml-1.5">
                        {{ row.original.user_id }}
                        <template v-if="row.original.user?.grade != null"> · {{ row.original.user.grade }}학년 {{ row.original.user.number }}반</template>
                    </span>
                    <span v-if="row.original.class_grade != null" class="ml-2 text-primary">
                        → {{ row.original.class_grade }}학년 {{ row.original.class_number }}반
                    </span>
                </template>
                <template #amount-cell="{ row }">
                    <UBadge v-if="row.original.class_grade != null" color="info" variant="subtle">
                        {{ row.original.user?.type === 'teacher' ? '학급 전달' : '학급 지급' }} {{ -row.original.amount }}
                    </UBadge>
                    <UBadge v-else :color="row.original.amount > 0 ? 'success' : 'error'" variant="subtle">
                        {{ row.original.amount > 0 ? `+${row.original.amount}` : row.original.amount }}
                    </UBadge>
                </template>
                <template #actor_id-cell="{ row }">
                    <span>{{ row.original.actor?.name ?? '-' }}</span>
                    <span class="text-muted ml-1.5" v-if="row.original.actor_id != null">{{ row.original.actor_id }}</span>
                </template>
                <template #memo-cell="{ row }">
                    <span class="text-muted">{{ row.original.memo ?? '' }}</span>
                </template>
            </UTable>
            <UPagination v-model:page="dataPage" :total="maxPage" :items-per-page="1" v-if="maxPage > 1" class="mt-4" />
        </template>
    </UDashboardPanel>
</template>
