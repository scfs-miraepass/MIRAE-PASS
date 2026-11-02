<script setup lang="ts">
import { karaokeTimeLabel, karaokeErrorMessage } from "@/utils/karaoke";
import KaraokeHeader from "~/components/karaoke/header.vue";
import InviteCard from "~/components/karaoke/invites/card.vue";

definePageMeta({
    permissions: [UserPermission.JOIN_KARAOKE] as PermissionCondition,
});

const toast = useToast();

interface InviteRow {
    partyId: number;
    karaokeId: number;
    leaderName: string;
    dateLabel: string;
    timeLabel: string;
    deciding: boolean;
}

const rows = ref<InviteRow[]>([]);
const pending = ref<boolean>(true);

const load = async () => {
    pending.value = true;
    const invitesReq = await $API.getMyKaraokePartyInvites();
    if (invitesReq.error || !invitesReq.data) {
        pending.value = false;
        return;
    }

    const pendingInvites = invitesReq.data.data.filter((i) => i.pending);
    const resolved = await Promise.all(
        pendingInvites.map(async (invite): Promise<InviteRow | null> => {
            const partyReq = await $API.getKaraokeParty({ path: { party_id: invite.party_id } });
            if (partyReq.error) return null;
            const karaokeReq = await $API.getKaraoke({ path: { karaoke_id: partyReq.data.data.auction_id } });
            if (karaokeReq.error) return null;

            return {
                partyId: invite.party_id,
                karaokeId: partyReq.data.data.auction_id,
                leaderName: partyReq.data.data.leader.name,
                dateLabel: new Date(karaokeReq.data.data.date).toLocaleDateString("ko-KR", {
                    month: "long",
                    day: "numeric",
                }),
                timeLabel: karaokeTimeLabel(karaokeReq.data.data.time),
                deciding: false,
            };
        }),
    );

    rows.value = resolved.filter((r): r is InviteRow => r !== null);
    pending.value = false;
};

await load();

const decide = async (row: InviteRow, accept: boolean) => {
    row.deciding = true;
    const req = await $API.decideKaraokePartyInvite({
        path: { party_id: row.partyId },
        body: { accept },
    });
    row.deciding = false;

    if (req.error) {
        toast.add({ title: "처리하지 못했어요.", description: karaokeErrorMessage(req.error), color: "error" });
        return;
    }

    rows.value = rows.value.filter((r) => r.partyId !== row.partyId);

    if (accept) {
        toast.add({ title: "초대를 수락했어요.", color: "success" });
        navigateTo(`/karaoke/${row.karaokeId}`);
    }
};
</script>

<template>
    <!-- 상단 헤더: 뒤로가기 + 제목 -->
    <KaraokeHeader to="/karaoke" title="파티 초대함" />

    <!-- 초대 목록: 로딩/빈 상태 및 초대 카드 -->
    <div class="flex-1 flex flex-col gap-2">
        <template v-if="pending">
            <USkeleton v-for="i in 3" :key="i" class="w-full h-20 rounded-2xl" />
        </template>
        <div
            class="flex-1 flex flex-col items-center justify-center text-ui-p1 opacity-50 py-16"
            v-else-if="rows.length <= 0"
        >
            <UIcon name="i-ph-bell-slash" class="text-h2 mb-1.5" />
            받은 초대가 없어요.
        </div>
        <InviteCard
            v-else
            v-for="row in rows"
            :key="row.partyId"
            :leader-name="row.leaderName"
            :date-label="row.dateLabel"
            :time-label="row.timeLabel"
            :deciding="row.deciding"
            @decide="(accept) => decide(row, accept)"
        />
    </div>
</template>
