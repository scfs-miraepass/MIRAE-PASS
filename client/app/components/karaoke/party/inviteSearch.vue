<script setup lang="ts">
import type { User } from "@/client";
import { karaokeErrorMessage } from "@/utils/karaoke";

const props = defineProps<{
    partyId: number;
    canSearch: boolean;
    takenIds: Set<number>;
}>();
const emit = defineEmits<{ invited: [user: User] }>();

const toast = useToast();
const session = useSession();

const search = ref<string>("");
const searchResult = ref<User[]>([]);
const searching = ref<boolean>(false);
const invitingId = ref<number | null>(null);
let searchTimeout: ReturnType<typeof setTimeout>;

const onSearchInput = (event: InputEvent) => {
    search.value = (event.target as HTMLInputElement).value;
    clearTimeout(searchTimeout);
    const q = search.value.replaceAll(" ", "");
    if (q.length <= 0) {
        searchResult.value = [];
        return;
    }
    searchTimeout = setTimeout(async () => {
        searching.value = true;
        const req = await $API.searchSearchGet({ query: { q, t: ["student", "teacher"] } });
        searching.value = false;
        if (req.error) {
            toast.add({ title: "검색하지 못했어요.", description: karaokeErrorMessage(req.error), color: "error" });
            return;
        }
        searchResult.value = req.data.data.filter((u) => u.id !== session.value?.id);
    }, 200);
};

const invite = async (user: User) => {
    invitingId.value = user.id!;
    const req = await $API.inviteKaraokePartyMember({
        path: { party_id: props.partyId },
        body: { user_id: user.id! },
    });
    invitingId.value = null;

    if (req.error) {
        toast.add({ title: "초대하지 못했어요.", description: karaokeErrorMessage(req.error), color: "error" });
        return;
    }
    toast.add({ title: `${user.name}님을 초대했어요.`, color: "success" });
    emit("invited", user);
};
</script>

<template>
    <div class="rounded-2xl light:bg-default dark:bg-muted p-6">
        <p class="text-ui-p2 light:text-black/50 dark:text-white/50 mb-3">멤버 초대</p>
        <UInput
            type="text"
            size="xl"
            class="w-full"
            icon="i-ph-magnifying-glass"
            placeholder="이름 또는 학번"
            :ui="{ base: 'rounded-xl' }"
            :model-value="search"
            :disabled="!canSearch"
            @input="onSearchInput"
        />
        <p class="text-ui-p2 text-error mt-5" v-if="!canSearch">
            유저 검색 권한이 없어요. 담당자에게 문의해주세요.
        </p>
        <div class="flex flex-col" v-if="searching">
            <p class="text-ui-p2 opacity-50">검색중..</p>
        </div>
        <div class="flex flex-col space-y-4 mt-5" v-else-if="search.length > 0">
            <p class="text-ui-p2 opacity-50" v-if="searchResult.length <= 0">찾지 못했어요.</p>
            <div
                v-else
                v-for="u in searchResult"
                :key="u.id!"
                class="flex items-center justify-between"
            >
                <p class="text-p2">{{ u.name }}{{ u.number ? ` (${u.grade}학년 ${u.number}반)` : "" }}</p>
                <UButton
                    size="md"
                    class="rounded-lg"
                    :disabled="takenIds.has(u.id!) || invitingId === u.id"
                    :loading="invitingId === u.id"
                    @click="invite(u)"
                >
                    {{ takenIds.has(u.id!) ? "초대됨" : "초대" }}
                </UButton>
            </div>
        </div>
    </div>
</template>
