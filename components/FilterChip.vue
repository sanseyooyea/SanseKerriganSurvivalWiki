<template>
  <button
    type="button"
    class="rounded-md border px-2.5 py-1 text-xs transition-all duration-150
           focus:outline-none focus-visible:ring-2 focus-visible:ring-survivor-500/40
           active:translate-y-px"
    :class="active
      ? 'border-survivor-600 bg-survivor-600 text-white shadow-sm dark:border-survivor-500 dark:bg-survivor-500'
      : 'border-surface-200 text-gray-600 hover:border-surface-300 hover:bg-surface-50 dark:border-gray-700 dark:text-gray-300 dark:hover:border-gray-600 dark:hover:bg-gray-700/40'"
    :aria-pressed="active"
    @click="$emit('click')"
  >
    <slot />
  </button>
</template>

<script setup lang="ts">
defineProps<{ active?: boolean }>()
defineEmits<{ click: [] }>()
</script>
