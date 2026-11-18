<script setup lang="ts">
import Form from './inputForm.vue'
import type { SubmitEmit } from './inputForm.vue'

const emit = defineEmits<{
    'submit': [password: string]
}>()

const toast = useToast();
const password = ref<string>('');
const confirm_password = ref<string>('');
const isConfirm = ref<boolean>(false);

const onSubmit = ({ error, inputVibration }: SubmitEmit) => {
    error.value = false;
    if (!isConfirm.value) {
        if (password.value.length != 6) return;
        isConfirm.value = true;
        return;
    }

    if (confirm_password.value.length != 6) return;
    if (confirm_password.value != password.value) {
        error.value = true;
        inputVibration()
        confirm_password.value = '';
        toast.add({ title: '비밀번호가 맞지 않습니다.', color: 'error' })
        return;
    }

    // 최종적으로 요청 날리는건 부모(kiosk.vue)에서 할꺼임. 기존에 비밀번호가 있다면 같이 넣어서 보내줘야 해서;;
    emit('submit', password.value)
}
</script>

<template>
    <Form
        title="설정하려는 비밀번호 입력"
        description="카페 등 키오스크에서 결제시 사용되요"
        v-model="password"
        @submit="onSubmit"
        v-if="!isConfirm"
    />
    <Form
        title="비밀번호 재입력"
        description="비밀번호를 한번더 입력해주세요"
        v-model="confirm_password"
        @submit="onSubmit"
        v-else
    />
</template>