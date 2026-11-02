<script setup lang="ts">
import type { KaraokeCreate } from '@/client'
import { todayDateString } from '@/utils/karaoke'

const emit = defineEmits(['close', 'create'])
const toast = useToast()

const open = ref<boolean>(true)
const loading = ref<boolean>(false)
const today = todayDateString()

const timeOptions = [
    { label: '1교시', value: 1 },
    { label: '2교시', value: 2 },
    { label: '3교시', value: 3 },
    { label: '4교시', value: 4 },
    { label: '5교시', value: 5 },
    { label: '6교시', value: 6 },
    { label: '7교시', value: 7 },
    { label: '점심시간', value: 8 }
]

const form = ref({
    date: today,
    time: 1,
    startTime: '',
    endTime: '',
    minPoint: 0
})

watch(open, value => {
    if (!value) {
        setTimeout(() => emit('close'), 200)
    }
})

const onSubmit = async () => {
    if (!form.value.date) {
        toast.add({ title: '일자를 입력해주세요.', color: 'error' })
        return
    }
    if (form.value.date < today) {
        toast.add({ title: '과거 일자에는 경매를 생성할 수 없습니다.', color: 'error' })
        return
    }
    if (!form.value.startTime || !form.value.endTime) {
        toast.add({ title: '경매 시작/종료 시간을 입력해주세요.', color: 'error' })
        return
    }
    if (new Date(form.value.endTime) <= new Date(form.value.startTime)) {
        toast.add({ title: '종료 시간을 확인해주세요.', description: '종료 시간은 시작 시간보다 늦어야 합니다.', color: 'error' })
        return
    }
    if (form.value.minPoint % 100 !== 0) {
        toast.add({ title: '최소 입찰가를 확인해주세요.', description: '최소 입찰가는 100포인트 단위로 입력해야 합니다.', color: 'error' })
        return
    }

    loading.value = true

    // 서버는 date/start_time/end_time을 문자열(ISO date, ISO datetime)로 검증하므로
    // 생성된 타입이 명시하는 Date가 아닌 문자열 그대로 전달해야 한다.
    const body = {
        date: form.value.date,
        time: form.value.time,
        start_time: new Date(form.value.startTime).toISOString(),
        end_time: new Date(form.value.endTime).toISOString(),
        min_point: form.value.minPoint
    } as unknown as KaraokeCreate

    const req = await $API.createKaraoke({ body })

    if (req.error) {
        const status = req.response?.status
        toast.add({
            title: status === 409 ? '이미 존재하는 경매입니다.' : '문제가 발생했습니다.',
            description: status === 409
                ? '같은 일자/시간대의 경매가 이미 존재합니다.'
                : '지속적으로 발생하는 경우 관리자에게 문의 바랍니다.',
            color: 'error'
        })
        loading.value = false
        return
    }

    toast.add({
        title: '정상적으로 처리되었습니다.',
        description: '노래방 경매가 생성되었습니다.',
        color: 'success'
    })

    open.value = false
    emit('create')
}
</script>

<template>
    <UModal
        title="노래방 경매 생성"
        description="특정 일자/시간대의 노래방 경매를 생성합니다."
        v-model:open="open"
        :close="false"
        :dismissible="!loading"
    >
        <template #body>
            <form @submit.prevent="onSubmit" class="space-y-4">
                <div class="flex gap-4">
                    <UFormField label="일자" name="date" class="flex-1">
                        <UInput v-model="form.date" type="date" :min="today" class="w-full" />
                    </UFormField>
                    <UFormField label="시간" name="time" class="w-32">
                        <USelect v-model="form.time" :items="timeOptions" class="w-full" />
                    </UFormField>
                </div>
                <div class="flex gap-4">
                    <UFormField label="경매 시작 시간" name="start_time" class="flex-1">
                        <UInput v-model="form.startTime" type="datetime-local" class="w-full" />
                    </UFormField>
                    <UFormField label="경매 종료 시간" name="end_time" class="flex-1">
                        <UInput v-model="form.endTime" type="datetime-local" class="w-full" />
                    </UFormField>
                </div>
                <UFormField label="최소 입찰가" name="min_point" description="100포인트 단위로 입력해주세요.">
                    <UInput v-model="form.minPoint" type="number" min="0" step="100" placeholder="미입력 시 0" class="w-full" />
                </UFormField>
            </form>
        </template>
        <template #footer>
            <div class="flex justify-end gap-2 w-full">
                <UButton label="취소" color="neutral" variant="ghost" :disabled="loading" @click="open = false" />
                <UButton label="생성" color="primary" :loading="loading" @click="onSubmit" />
            </div>
        </template>
    </UModal>
</template>
