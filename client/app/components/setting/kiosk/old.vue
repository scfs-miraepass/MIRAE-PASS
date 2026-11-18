<script setup lang="ts">
import Form from './inputForm.vue'
import type { SubmitEmit } from './inputForm.vue'

const emit = defineEmits<{
    'verify': [password: string]
}>()

const toast = useToast();
const session = useSession();
const password = ref<string>('');

const onSubmit = async ({ error, inputVibration }: SubmitEmit) => {
    if (session.value == undefined) return
    error.value = false;

    const req = await $API.kioskPasswordVerify({
        body: {
            id: session.value.id!,
            password: password.value
        }
    })
    if (req.error) {
        // TODO: 언젠기는 내가 에러처리 하겠지
        return;
    }

    // kioskPasswordVerify는 설정된 비밀번호와 입력한 비밀번호가 같은지를, data에 True/False으로 응답합니다.
    if (!req.data.data) {
        error.value = true;
        inputVibration()
        password.value = '';
        toast.add({ title: '비밀번호가 맞지 않습니다.', color: 'error' })
        return;
    }

    // 부모(kiosk.vue)으로 넘겨서 진행합니다.
    emit('verify', password.value)
}
</script>

<template>
    <Form
        title="기존 비밀번호 입력"
        description="키오스크 비밀번호 변경을 위해서는 기존 비밀번호를 입력해주세요"
        @submit="onSubmit"
        v-model="password"
    />
</template>