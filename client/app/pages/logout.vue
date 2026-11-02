<script setup lang="ts">

definePageMeta({
    layout: false,
});
const session = useSession();
const { lastFetched } = useAuth();

onMounted(async () => {
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
