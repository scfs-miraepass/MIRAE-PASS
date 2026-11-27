<script setup lang="ts">

definePageMeta({
    layout: false,
});
const session = useSession();
const { lastFetched } = useAuth();

const push = usePushNotification();

onMounted(async () => {
    // 공용 기기에서 다음 사용자에게 이전 사용자의 알림이 가지 않도록, 로그아웃 전에 이 기기의 알림 구독을 해제합니다.
    await push.disable().catch(() => undefined);
    const req = await $API.logoutAuthLogoutPost();
    if (!req.error) {
        session.value = undefined;
        lastFetched.value = Date.now();
        await navigateTo("/login", { replace: true });
    }
});
</script>

<template>
    <div class="w-screen h-screen flex items-center justify-center text-p1">
        <USkeleton class="bg-transparent flex flex-col items-center">
            <LogoSymbol class="mb-2" />
            로그아웃 중이에요.. 잠시만 기다려주세요.
        </USkeleton>
    </div>
</template>
