<script setup lang="ts">
import { UserPermission, type NotificationSend, type NotificationTargetType, type User, type UserType } from "@miraepass/api-client";

definePageMeta({
    permissions: [ UserPermission.SEND_NOTIFICATION ],
});

// 서버 NotificationSend 모델의 길이 제한과 맞춥니다.
const TITLE_MAX_LENGTH = 50;
const BODY_MAX_LENGTH = 200;

const toast = useToast();

const TARGET_OPTIONS: { label: string; value: NotificationTargetType }[] = [
    { label: "전체", value: "all" },
    { label: "계정 종류", value: "user_type" },
    { label: "학년 · 반", value: "class" },
    { label: "유저 선택", value: "users" },
];
const USER_TYPE_OPTIONS: { label: string; value: UserType }[] = [
    { label: "학생", value: "student" },
    { label: "교사", value: "teacher" },
    { label: "서비스 계정", value: "service" },
];

const title = ref<string>("");
const body = ref<string>("");
const url = ref<string>("/");
const target = ref<NotificationTargetType>("all");
const userType = ref<UserType>("student");
const grade = ref<number | undefined>(1);
const classNumber = ref<number | undefined>();
const selectedUsers = ref<User[]>([]);
const sending = ref<boolean>(false);
const confirmOpen = ref<boolean>(false);

// 유저 검색 (유저 선택 대상)
const search = ref<string>("");
const searchLoading = ref<boolean>(false);
const searchUsers = ref<User[]>([]);
let searchTimeout: ReturnType<typeof setTimeout> | undefined;

const onSearch = (event: InputEvent) => {
    search.value = (event.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
        if (search.value.replaceAll(" ", "").length <= 0) {
            searchUsers.value = [];
            return;
        }
        searchLoading.value = true;
        const req = await $API.searchSearchGet({ query: { q: search.value, t: ["student", "teacher", "service"] } });
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

const addUser = (user: User) => {
    if (!selectedUsers.value.some((u) => u.id === user.id)) selectedUsers.value.push(user);
    searchUsers.value = [];
    search.value = "";
};
const removeUser = (user: User) => {
    selectedUsers.value = selectedUsers.value.filter((u) => u.id !== user.id);
};

const targetLabel = computed(() => {
    switch (target.value) {
        case "all":
            return "전체 사용자";
        case "user_type":
            return `${USER_TYPE_OPTIONS.find((o) => o.value === userType.value)?.label} 전체`;
        case "class":
            return classNumber.value ? `${grade.value}학년 ${classNumber.value}반 학생` : `${grade.value}학년 학생 전체`;
        case "users":
            return `선택한 사용자 ${selectedUsers.value.length}명`;
    }
});

const canSend = computed(() => {
    if (!title.value.trim() || !body.value.trim()) return false;
    if (!url.value.startsWith("/") || url.value.startsWith("//")) return false;
    if (target.value === "class" && !grade.value) return false;
    if (target.value === "users" && selectedUsers.value.length === 0) return false;
    return true;
});

const send = async () => {
    const payload: NotificationSend = {
        title: title.value.trim(),
        body: body.value.trim(),
        url: url.value,
        target: target.value,
        user_type: target.value === "user_type" ? userType.value : null,
        grade: target.value === "class" ? grade.value : null,
        number: target.value === "class" ? classNumber.value || null : null,
        user_ids: target.value === "users" ? selectedUsers.value.map((u) => u.id!) : null,
    };

    sending.value = true;
    const req = await $API.sendNotification({ body: payload });
    sending.value = false;
    confirmOpen.value = false;
    if (req.error) {
        toast.add({ title: "알림을 보내지 못했어요.", description: stickerErrorMessage(req.error), color: "error" });
        return;
    }
    const result = req.data.data;
    toast.add({
        title: "알림을 보내기 시작했어요.",
        description: `대상 ${result.target_users}명 · 알림을 켠 기기 ${result.subscriptions}대`,
        color: "success",
    });
    title.value = "";
    body.value = "";
};
</script>

<template>
    <UModal v-model:open="confirmOpen" title="알림 보내기" :ui="{ footer: 'justify-end' }">
        <template #body>
            <p class="text-sm"><span class="font-semibold">{{ targetLabel }}</span>에게 알림을 보낼까요? 보낸 알림은 취소할 수 없어요.</p>
        </template>
        <template #footer>
            <UButton color="neutral" variant="outline" @click="confirmOpen = false">취소</UButton>
            <UButton :loading="sending" @click="send">보내기</UButton>
        </template>
    </UModal>

    <UDashboardPanel :ui="{ root: 'overflow-y-auto', body: 'min-h-fit' }">
        <template #header>
            <UDashboardNavbar title="알림 보내기">
                <template #leading>
                    <UDashboardSidebarCollapse />
                </template>
            </UDashboardNavbar>
        </template>

        <template #body>
            <div class="grid gap-8 lg:grid-cols-[minmax(0,32rem)_minmax(0,22rem)]">
                <div class="flex flex-col gap-5">
                    <UFormField label="제목" required :hint="`${title.length}/${TITLE_MAX_LENGTH}`">
                        <UInput v-model="title" :maxlength="TITLE_MAX_LENGTH" placeholder="예: 내일 체육대회 안내" class="w-full" />
                    </UFormField>
                    <UFormField label="내용" required :hint="`${body.length}/${BODY_MAX_LENGTH}`">
                        <UTextarea v-model="body" :maxlength="BODY_MAX_LENGTH" :rows="4" autoresize class="w-full" />
                    </UFormField>
                    <UFormField label="눌렀을 때 열 화면" help="앱 안 경로입니다. 예: / (홈), /notices (공지사항)">
                        <UInput v-model="url" placeholder="/" class="w-full" />
                    </UFormField>

                    <UFormField label="받는 사람" required>
                        <URadioGroup v-model="target" :items="TARGET_OPTIONS" orientation="horizontal" />
                    </UFormField>

                    <UFormField v-if="target === 'user_type'" label="계정 종류">
                        <USelect v-model="userType" :items="USER_TYPE_OPTIONS" class="w-48" />
                    </UFormField>

                    <div v-if="target === 'class'" class="flex gap-3">
                        <UFormField label="학년" required>
                            <UInputNumber v-model="grade" :min="1" :max="9" class="w-32" />
                        </UFormField>
                        <UFormField label="반" help="비우면 학년 전체">
                            <UInputNumber v-model="classNumber" :min="1" :max="99" class="w-32" />
                        </UFormField>
                    </div>

                    <div v-if="target === 'users'" class="flex flex-col gap-2">
                        <div class="relative w-full">
                            <UInput
                                :model-value="search"
                                @input="onSearch"
                                icon="i-lucide-search"
                                placeholder="이름 또는 학번 검색..."
                                class="w-full"
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
                                    @click="addUser(u)"
                                >
                                    <span>{{ u.name }}</span>
                                    <span class="text-muted">{{ u.id }}<template v-if="u.grade != null"> · {{ u.grade }}학년 {{ u.number }}반</template></span>
                                </button>
                            </div>
                        </div>
                        <div v-if="selectedUsers.length" class="flex flex-wrap gap-1.5">
                            <UBadge
                                v-for="u in selectedUsers"
                                :key="u.id!"
                                color="neutral"
                                variant="subtle"
                                class="cursor-pointer"
                                trailing-icon="i-lucide-x"
                                @click="removeUser(u)"
                            >
                                {{ u.name }} ({{ u.id }})
                            </UBadge>
                        </div>
                        <p v-else class="text-sm text-muted">검색해서 받을 사람을 추가하세요.</p>
                    </div>

                    <div class="flex items-center gap-3">
                        <UButton icon="i-lucide-send" :disabled="!canSend" @click="confirmOpen = true">보내기</UButton>
                        <p class="text-sm text-muted">{{ targetLabel }} · 앱에서 알림을 켠 기기에만 전송됩니다.</p>
                    </div>
                </div>

                <!-- 미리보기 -->
                <div>
                    <p class="text-sm text-muted mb-2">미리보기</p>
                    <div class="rounded-2xl border border-default bg-elevated/50 p-4 flex gap-3">
                        <div class="size-10 shrink-0 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                            <UIcon name="i-lucide-bell" class="size-5" />
                        </div>
                        <div class="min-w-0">
                            <p class="font-semibold text-sm truncate">{{ title || "제목" }}</p>
                            <p class="text-sm text-muted whitespace-pre-line break-words">{{ body || "내용" }}</p>
                        </div>
                    </div>
                </div>
            </div>
        </template>
    </UDashboardPanel>
</template>
