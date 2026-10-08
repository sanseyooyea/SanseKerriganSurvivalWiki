<template>
  <div class="flex flex-wrap items-center gap-1.5">
    <span class="w-12 shrink-0 text-xs text-gray-500 dark:text-gray-400">{{ label }}</span>
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{ label: string }>()
</script>
