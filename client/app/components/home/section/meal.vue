<script setup lang="ts">
import PageButton from "~/components/setting/object.vue";
</script>

<template>
    <NuxtLink to="/system/meal" v-slot="{ navigate }" custom>
        <PageButton @click="navigate()" icon="i-ph-bowl-food" label="급식" />
    </NuxtLink>
</template>
