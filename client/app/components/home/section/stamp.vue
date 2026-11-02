<script setup lang="ts">
import PageButton from "~/components/setting/object.vue";
</script>

<template>
    <NuxtLink to="/system/stamp" v-slot="{ navigate }" custom>
        <PageButton @click="navigate()" icon="material-symbols-light:festival-rounded" label="'학생의 날' 스탬프" />
    </NuxtLink>
</template>