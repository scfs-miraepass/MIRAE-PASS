<script setup lang="ts">
import type { KaraokePartyDetail, User } from "@/client";
import { karaokeErrorMessage } from "@/utils/karaoke";
import KaraokeHeader from "~/components/karaoke/header.vue";
import LeaderCard from "~/components/karaoke/party/leaderCard.vue";
import MembersCard from "~/components/karaoke/party/membersCard.vue";
import InviteSearch from "~/components/karaoke/party/inviteSearch.vue";
import PartyActions from "~/components/karaoke/party/actions.vue";

definePageMeta({
    permissions: [UserPermission.JOIN_KARAOKE] as PermissionCondition,
});

const route = useRoute();
const toast = useToast();
const session = useSession();
const karaokeId = computed(() => Number(route.params.id));

const party = ref<KaraokePartyDetail | null>(null);
const pending = ref<boolean>(true);
const busy = ref<boolean>(false);

const isLeader = computed(() => !!party.value && party.value.leader_id === session.value?.id);

const load = async () => {
    pending.value = true;
    const req = await $API.getMyKaraokeParty({ path: { karaoke_id: karaokeId.value } });
    party.value = req.error ? null : req.data.data;
    pending.value = false;
    if (!party.value) navigateTo(`/karaoke/${karaokeId.value}`, { replace: true });
};

await load();

const canSearch = computed(() => hasPermission(session.value?.permissions, UserPermission.SEARCH_USER));

const takenIds = computed(() => {
    if (!party.value) return new Set<number>();
    return new Set<number>([
        party.value.leader_id,
        ...party.value.members.map((m) => m.id!),
        ...party.value.pending_members.map((m) => m.id!),
    ]);
});

const kick = async (user: User) => {
    busy.value = true;
    const req = await $API.kickKaraokePartyMember({
        path: { party_id: party.value!.id, user_id: user.id! },
    });
    busy.value = false;

    if (req.error) {
        toast.add({ title: "내보내지 못했어요.", description: karaokeErrorMessage(req.error), color: "error" });
        return;
    }
    party.value = req.data.data;
    toast.add({ title: `${user.name}님을 내보냈어요.`, color: "success" });
};

const leave = async () => {
    busy.value = true;
    const req = await $API.leaveKaraokeParty({ path: { party_id: party.value!.id } });
    busy.value = false;

    if (req.error) {
        toast.add({ title: "탈퇴하지 못했어요.", description: karaokeErrorMessage(req.error), color: "error" });
        return;
    }
    toast.add({ title: "파티에서 나왔어요.", color: "success" });
    navigateTo(`/karaoke/${karaokeId.value}`, { replace: true });
};

const disperse = async () => {
    busy.value = true;
    const req = await $API.disperseKaraokeParty({ path: { party_id: party.value!.id } });
    busy.value = false;

    if (req.error) {
        toast.add({ title: "해산하지 못했어요.", description: karaokeErrorMessage(req.error), color: "error" });
        return;
    }
    toast.add({ title: "파티를 해산했어요.", color: "success" });
    navigateTo(`/karaoke/${karaokeId.value}`, { replace: true });
};
</script>

<template>
    <!-- 상단 헤더: 뒤로가기 + 제목 -->
    <KaraokeHeader :to="`/karaoke/${karaokeId}`" title="파티 관리" />

    <div class="flex-1 flex flex-col items-center justify-center text-ui-p1 opacity-50" v-if="pending">
        <UIcon name="i-ph-spinner-gap" class="text-h2 mb-1.5 animate-spin" />
        불러오는 중..
    </div>

    <div class="flex-1 flex flex-col gap-3" v-else-if="party">
        <!-- 파티장 정보 -->
        <LeaderCard :leader="party.leader" />

        <!-- 참여 멤버 + 초대 대기중 목록 -->
        <MembersCard
            :members="party.members"
            :pending-members="party.pending_members"
            :is-leader="isLeader"
            :busy="busy"
            @kick="kick"
        />

        <!-- 멤버 검색 + 초대 (파티장 전용) -->
        <InviteSearch
            v-if="isLeader"
            :party-id="party.id"
            :can-search="canSearch"
            :taken-ids="takenIds"
            @invited="load"
        />

        <div class="flex-1" />

        <!-- 하단 액션: 파티 해산(파티장) / 파티 나가기(멤버) -->
        <PartyActions :is-leader="isLeader" :busy="busy" @disperse="disperse" @leave="leave" />
    </div>
</template>
