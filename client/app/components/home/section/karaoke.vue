<script setup lang="ts">
import PageButton from "~/components/setting/object.vue";
</script>

<template>
    <NuxtLink to="/karaoke" v-slot="{ navigate }" custom>
        <PageButton @click="navigate()" icon="i-ph-microphone-stage" label="노래방 예약" value="BETA" />
    </NuxtLink>
</template>
