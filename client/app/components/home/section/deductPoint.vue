<script setup lang="ts">
import PageButton from "~/components/setting/object.vue";

const session = useSession();
</script>

<template>
    <NuxtLink to="/system/userSelect?a=deduct-point" v-slot="{ navigate }" custom>
        <PageButton @click="navigate()" icon="i-ph-money" :label="`포인트 ${session?.type == 'service'? '결제':'차감'}`" />
    </NuxtLink>
</template>