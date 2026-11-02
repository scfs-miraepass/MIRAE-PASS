<script setup lang="ts">
import type { KaraokeResponse, KaraokeFinalBidResponse } from '@/client'
import { karaokeTimeLabel } from '@/utils/karaoke'

const { karaoke } = defineProps<{
    karaoke: KaraokeResponse
}>()
const emit = defineEmits(['close'])
const toast = useToast()

const open = ref<boolean>(true)
const loading = ref<boolean>(true)
const noBids = ref<boolean>(false)
const finalBid = ref<KaraokeFinalBidResponse | null>(null)

watch(open, value => {
    if (!value) {
        setTimeout(() => emit('close'), 200)
    }
})

onMounted(async () => {
    const req = await $API.getKaraokeFinalBid({
        path: {
            karaoke_id: karaoke.id!
        }
    })

    if (req.error) {
        if (req.response?.status === 404) {
            noBids.value = true
        } else {
            toast.add({
                title: '낙찰자 정보를 불러오지 못했습니다.',
                description: '지속적으로 발생하는 경우 관리자에게 문의 바랍니다.',
                color: 'error'
            })
        }
        loading.value = false
        return
    }

    finalBid.value = req.data!.data
    loading.value = false
})
</script>

<template>
    <UModal
        :title="`${String(karaoke.date)} ${karaokeTimeLabel(karaoke.time)} 낙찰 결과`"
        v-model:open="open"
        :ui="{ footer: 'justify-end' }"
    >
        <template #body>
            <div v-if="loading" class="flex justify-center py-6">
                <UIcon name="i-lucide-loader-2" class="animate-spin size-6" />
            </div>
            <div v-else-if="finalBid" class="space-y-2">
                <p><span class="text-muted">낙찰자</span> — <span class="font-semibold">{{ finalBid.bidder.name }}</span></p>
                <p><span class="text-muted">낙찰 금액</span> — <span class="font-semibold text-primary">{{ finalBid.amount.toLocaleString() }} P</span></p>
                <p v-if="finalBid.party_id"><span class="text-muted">파티 ID</span> — {{ finalBid.party_id }}</p>
            </div>
            <p v-else-if="noBids" class="text-muted">입찰 내역이 없습니다.</p>
        </template>
        <template #footer>
            <UButton label="닫기" color="neutral" variant="ghost" @click="open = false" />
        </template>
    </UModal>
</template>
