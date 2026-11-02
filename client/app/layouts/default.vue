<script setup lang="ts">
const session = useSession()
</script>

<template>
    <div class="w-screen min-h-screen p-5 flex flex-col" v-if="session != null">
        <slot />
    </div>
</template>