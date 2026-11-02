<script setup lang="ts">
import PageButton from "~/components/setting/object.vue";
</script>

<template>
    <NuxtLink to="/system/stamp" v-slot="{ navigate }" custom>
        <PageButton @click="navigate()" icon="material-symbols-light:festival-rounded" label="'탄소중립 동아리 페스티벌' 스탬프" />
    </NuxtLink>
</template>