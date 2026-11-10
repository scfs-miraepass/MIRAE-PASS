<script setup lang="ts">
import Section from "@/components/setting/section.vue";
import Obj from "@/components/setting/object.vue";
</script>

<template>
    <div class="flex items-center mb-4">
        <NuxtLink to="/setting" v-slot="{ navigate }" custom>
            <UButton @click="navigate()" color="neutral" variant="ghost" icon="i-ph-caret-left-bold" class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented" size="xl" />
        </NuxtLink>
        <p class="text-2xl font-bold text-gray-900 dark:text-white ml-1">키오스크 비밀번호 설정</p>
    </div>

    <div class="space-y-3">

    </div>
</template>