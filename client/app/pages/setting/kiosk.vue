<script setup lang="ts">
import newPassword from "@/components/setting/kiosk/newPassword.vue"

const session = useSession();
const isFirst = ref(true);

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

</script>

<template>
    <div class="flex items-center mb-4">
        <NuxtLink to="/setting" v-slot="{ navigate }" custom>
            <UButton @click="navigate()" color="neutral" variant="ghost" icon="i-ph-caret-left-bold" class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented" size="xl" />
        </NuxtLink>
        <p class="text-2xl font-bold text-gray-900 dark:text-white ml-1">키오스크 비밀번호 설정</p>
    </div>

    <newPassword />
</template>