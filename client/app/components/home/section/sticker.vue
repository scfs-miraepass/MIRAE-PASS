<script setup lang="ts">
import PageButton from "~/components/setting/object.vue";
</script>

<template>
    <NuxtLink to="/system/sticker" v-slot="{ navigate }" custom>
        <PageButton @click="navigate()" icon="i-ph-heart" label="스티커" />
    </NuxtLink>
</template>
