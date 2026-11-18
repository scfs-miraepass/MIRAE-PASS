<script setup lang="ts">
import PageButton from "~/components/setting/object.vue";
</script>

<template>
    <NuxtLink to="/system/userSelect?a=give-sticker" v-slot="{ navigate }" custom>
        <PageButton @click="navigate()" icon="i-ph-sticker" label="스티커 지급" />
    </NuxtLink>
</template>
