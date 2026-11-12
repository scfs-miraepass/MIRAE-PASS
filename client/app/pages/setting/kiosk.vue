<script setup lang="ts">
import newPassword from "@/components/setting/kiosk/new.vue"
import oldPassword from "@/components/setting/kiosk/old.vue"

const toast = useToast();
const session = useSession();
const isFirst = ref(true);
const old_password = ref<string>("");

await useAsyncData(
    'settings.kioskPassword',
    async (_nuxtApp, { signal }) => {
        if (!session.value) return
        const req = await $API.kioskPasswordVerify({
            body: {
                id: session.value.id!,
                password: ""
            },
            ...signal
        })
        if (req.response == undefined) return;

        // kioskPasswordVerify는 비밀번호가 설정되지 않았을 경우 400을 응답합니다.
        isFirst.value = req.response.status == 400;

        return req
    }
)

const onVerify = (password: string) => {
    /*
    기존 비밀번호 확인(oldPassword)에서 기존 비밀번호가 일치하면 호출됩니다.
     */

    old_password.value = password
}

const onSubmit = async (password: string) => {
    /*
    비밀번호를 업데이트하는 경우 호출됩니다.
     */

    const req = await $API.changeKioskPassword({
        body: {
            old_password: old_password.value,
            new_password: password
        }
    })

    if (req.error) {
        // TODO: 언젠기는 내가 에러처리 하겠지2
        return;
    }

    toast.add({ title: '키오스크 비밀번호가 업데이트 되었습니다.', color: 'success' })
    await navigateTo('/setting', { replace: true })
}

</script>

<template>
    <div class="flex items-center mb-4">
        <NuxtLink to="/setting" v-slot="{ navigate }" custom>
            <UButton @click="navigate()" color="neutral" variant="ghost" icon="i-ph-caret-left-bold" class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented" size="xl" />
        </NuxtLink>
        <p class="text-2xl font-bold text-gray-900 dark:text-white ml-1">키오스크 비밀번호 설정</p>
    </div>

    <oldPassword v-if="!isFirst && old_password.length <= 0" @verify="onVerify" />
    <newPassword v-if="(!isFirst && old_password.length > 0) || isFirst" @submit="onSubmit" />
</template>