<script setup lang="ts">
import type { UserType, User } from "@/client";
import { permissionsMiddleware } from "@/middleware/permissions.global";

const session = useSession()
const route = useRoute();

const actionList = computed<{
    [key: string]: {
        title: string;
        selectUrl: string;
        searchTarget: UserType[];
        permissions: PermissionCondition;
    }
}>(() => {
    return {
        "service-stamp": {
            title: "스탬프 지급",
            selectUrl: "/service/stamp",
            searchTarget: ["student", "teacher"],
            permissions: [ UserPermission.GIVE_STAMP ]
        },
        "grant-point": {
            title: "포인트 지급",
            selectUrl: "/system/pointProcessing?a=grant",
            searchTarget: session.value?.type == "teacher"? ["student"]:["student", "teacher"],
            permissions: [ UserPermission.GRANT_POINT ]
        },
        "deduct-point": {
            title: session.value?.type == "service"? "포인트 결제":"포인트 차감",
            selectUrl: "/system/pointProcessing?a=deduct",
            searchTarget: session.value?.type == "teacher"? ["student"]:["student", "teacher"],
            permissions: [ UserPermission.DEDUCT_POINT ]
        }
    }
})
const action = computed(() => actionList.value[route.query.a as string]!);

const search = ref<string>("");
const searchResult = ref<User[]>([]);
const hiddenResult = ref<boolean>(false);
const loadingResult = ref<boolean>(false);
let searchTimeout: any;
let beforeSearch: string = "";

watch(searchResult, () => {
    loadingResult.value = false;
    hiddenResult.value = false;
});

definePageMeta({
    middleware: [
        (to, from) => {
            if (!to.query.a || !actionList.value[to.query.a as string]) {
                return navigateTo("/", { replace: true });
            }
            return permissionsMiddleware(
                to,
                from,
                actionList.value[to.query.a as string]!.permissions,
            );
        },
    ],
});

const userSearch = async () => {
    const _search = search.value.replaceAll(" ", "");
    if (beforeSearch == _search) return;
    beforeSearch = _search;
    if (_search.length <= 0) {
        searchResult.value = [];
        return;
    }
    setTimeout(() => {
        if (hiddenResult.value) {
            loadingResult.value = true;
        }
    }, 350);
    const req = await $API.searchSearchGet({
        query: {
            q: _search,
            t: action.value.searchTarget,
        },
    });
    if (req.error) {
        // TODO: 에러 처리
        return;
    }
    searchResult.value = req.data.data;
};

const onSearchInput = async (event: InputEvent) => {
    hiddenResult.value = true;
    search.value = (event.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
        await userSearch();
    }, 200);
};

const onSelect = (user: User) => {
    const userData = useState<User | undefined>(
        "system.user-select.uesr",
        () => undefined,
    );
    userData.value = user;

    navigateTo(action.value.selectUrl);
};
</script>

<template>
    <div class="flex items-center mb-4">
        <NuxtLink to="/" v-slot="{ navigate }" custom>
            <UButton
                @click="navigate()"
                color="neutral"
                variant="ghost"
                icon="i-ph-caret-left-bold"
                class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented"
                size="xl"
            />
        </NuxtLink>
        <p class="text-2xl font-bold text-gray-900 dark:text-white ml-1">
            {{ action.title }}
        </p>
    </div>
    <div class="flex-1 flex flex-col">
        <UInput
            type="text"
            size="xl"
            class="w-full"
            icon="i-ph-magnifying-glass"
            placeholder="이름또는 학번"
            :ui="{ base: 'rounded-2xl' }"
            @input="onSearchInput"
            v-model="search"
        />
        <hr class="my-3 border-default" />
        <div
            class="px-1 py-2.5 light:bg-default dark:bg-muted rounded-2xl flex-1 overflow-y-scroll relative flex flex-col"
        >
            <div
                class="w-full h-full flex flex-col justify-center items-center transition-opacity duration-250 absolute top-0 left-0 pointer-events-none"
                :class="{ 'opacity-0!': !loadingResult }"
            >
                <USkeleton
                    class="flex flex-col justify-center items-center bg-transparent"
                >
                    <UIcon
                        name="i-ph-spinner-gap"
                        class="text-h2 mb-1.5 animate-spin"
                    />
                    검색중..
                </USkeleton>
            </div>
            <div
                class="flex-1 flex flex-col transition-opacity duration-250"
                :class="{
                    'max-h-0': searchResult.length > 0,
                    'opacity-0': hiddenResult,
                }"
            >
                <p
                    class="px-5 pt-4.5 pb-1.5 text-ui-p2 light:text-black/50 dark:text-white/50"
                >
                    {{ searchResult.length }}명의 사용자를 찾았어요.
                </p>
                <div
                    class="flex-1 flex flex-col items-center justify-center text-ui-p1 opacity-50"
                    v-if="searchResult.length <= 0"
                >
                    <UIcon
                        :name="
                            search.length > 0
                                ? 'i-ph-smiley-sad-thin'
                                : 'i-ph-magnifying-glass-thin'
                        "
                        class="text-h2 mb-1.5"
                    />
                    {{
                        search.length > 0
                            ? "찾지 못했어요."
                            : "지금 찾아보세요!"
                    }}
                </div>

                <button
                    class="px-5 py-4.5 rounded-xl flex flex-col items-start transition-all active:scale-95 active:opacity-50 active:bg-accented"
                    v-for="i in searchResult"
                    @click="onSelect(i)"
                >
                    <div class="flex items-center text-ui-p2">
                        <p
                            class="rounded-full bg-green-400 px-3 py-1.5 mr-2"
                            v-if="!i.number"
                        >
                            교사
                        </p>
                        <p
                            class="rounded-full bg-rose-400 px-3 py-1.5 mr-2"
                            v-else-if="i.number <= 2"
                        >
                            바이오메디컬과
                        </p>
                        <p
                            class="rounded-full bg-blue-400 px-3 py-1.5 mr-2"
                            v-else-if="i.number <= 4"
                        >
                            소프트웨어통신과
                        </p>
                        <p
                            class="rounded-full bg-yellow-400 px-3 py-1.5 mr-2"
                            v-else
                        >
                            IoT전기전자과
                        </p>
                        <template v-if="i.number"
                            >{{ i.grade }}학년 {{ i.number }}반</template
                        >
                    </div>
                    <p class="text-p0 mt-1.5">{{ i.name }}</p>
                </button>
            </div>
        </div>
    </div>
</template>
