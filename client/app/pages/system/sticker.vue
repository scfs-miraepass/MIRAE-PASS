<script setup lang="ts">
import type { StickerBalance } from "@miraepass/api-client";
import StickerRankingList from "@/components/sticker/rankingList.vue";
import StickerClassRanking from "@/components/sticker/classRanking.vue";

definePageMeta({
    permissions: [ UserPermission.VIEW_STICKER ],
});

const session = useSession();
const isStudent = computed(() => session.value?.type === "student");
const isTeacher = computed(() => session.value?.type === "teacher");
const showBalance = computed(() => isStudent.value || isTeacher.value);
const canGiveClass = computed(
    () => isTeacher.value && hasPermission(session.value?.permissions, UserPermission.GIVE_CLASS_STICKER),
);

const items = [
    {
        label: "개인 순위",
        icon: "i-ph-student",
        slot: "personal" as const,
    },
    {
        label: "학급 순위",
        icon: "i-ph-chalkboard-teacher",
        slot: "class" as const,
    },
];

const { data: myBalance } = await useAsyncData(
    "sticker.my_balance",
    async (_nuxtApp, { signal }): Promise<StickerBalance | null> => {
        if (!showBalance.value) return null;
        const req = await $API.getMyStickerBalance({ signal });
        if (req.error) return null;
        return req.data.data;
    },
);

const searchInput = ref<string>("");
const q = ref<string>("");
let searchTimeout: ReturnType<typeof setTimeout> | undefined;

const onSearchInput = (event: Event) => {
    searchInput.value = (event.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        q.value = searchInput.value.trim();
    }, 200);
};

onBeforeUnmount(() => {
    if (searchTimeout) clearTimeout(searchTimeout);
});
</script>

<template>
    <div class="flex items-center mb-4">
        <NuxtLink to="/" v-slot="{ navigate }" custom>
            <UButton @click="navigate()" color="neutral" variant="ghost" icon="i-ph-caret-left-bold" class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented" size="xl" />
        </NuxtLink>
        <p class="text-2xl font-bold text-gray-900 dark:text-white ml-1">스티커</p>
    </div>

    <!-- 내 스티커 (학생 / 교사) -->
    <div
        v-if="showBalance"
        class="rounded-3xl bg-elevated/60 px-6 py-5 mb-6 animate-fade-up-blur opacity-0"
    >
        <div class="flex items-center justify-between">
            <div>
                <p class="text-ui-p2 light:text-black/50 dark:text-white/50">내 스티커</p>
                <p class="text-h5 font-bold mt-0.5">
                    <UIcon name="i-ph-heart" class="inline-block align-[-2px]" /> {{ myBalance?.count ?? 0 }}개
                </p>
                <p class="text-ui-p2 mt-1 light:text-black/40 dark:text-white/40">
                    {{ isTeacher ? "받은 스티커를 학급에 전달할 수 있어요" : `매월 1일에 초기화돼요 · 한 주에 최대 ${myBalance?.max ?? 3}개` }}
                </p>
            </div>
            <div class="flex items-center gap-1.5">
                <span
                    v-for="i in (myBalance?.max ?? 3)"
                    :key="i"
                    class="tossface text-3xl"
                    :class="{ 'opacity-25 grayscale': i > (myBalance?.count ?? 0) }"
                >
                    💗
                </span>
            </div>
        </div>
        <NuxtLink v-if="canGiveClass" to="/system/stickerClass" v-slot="{ navigate }" custom>
            <UButton
                class="rounded-2xl justify-center flex py-3.5 w-full mt-4"
                icon="i-ph-paper-plane-tilt"
                :disabled="(myBalance?.count ?? 0) <= 0"
                @click="navigate()"
            >
                <p class="text-ui-p1 font-semibold">학급에 주기</p>
            </UButton>
        </NuxtLink>
    </div>

    <UTabs variant="link" :items="items" class="w-full" :ui="{ content: 'space-y-10 pt-6' }">
        <template #personal>
            <UInput
                type="text"
                :model-value="searchInput"
                @input="onSearchInput"
                icon="i-ph-magnifying-glass"
                placeholder="이름 또는 학번 검색"
                size="xl"
                class="w-full"
                :ui="{ base: 'rounded-2xl' }"
            />
            <StickerRankingList :q="q" />
        </template>
        <template #class>
            <StickerClassRanking />
        </template>
    </UTabs>
</template>
