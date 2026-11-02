<script setup lang="ts">
import PageButton from "~/components/setting/object.vue";

const stampType = useStampType();
</script>

<template>
    <NuxtLink :to="stampType? '/system/userSelect?a=service-stamp':'/service/stamp_setup'" v-slot="{ navigate }" custom>
        <PageButton @click="navigate()" icon="material-symbols-light:festival-rounded" label="'탄소중립 동아리 페스티벌' 스탬프 지급" />
    </NuxtLink>
</template>