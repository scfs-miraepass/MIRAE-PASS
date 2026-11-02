<script setup lang="ts">
import PageButton from "~/components/setting/object.vue";
</script>

<template>
    <NuxtLink to="/system/ranking" v-slot="{ navigate }" custom>
        <PageButton @click="navigate()" icon="i-ph-ranking" label="포인트 순위" />
    </NuxtLink>
</template>