<template>
  <span
    class="relative inline-flex shrink-0 items-center justify-center overflow-hidden
           rounded-md bg-surface-100 ring-1 ring-inset ring-black/5
           dark:bg-gray-700/60 dark:ring-white/10"
    :class="sizeClass"
  >
    <img
      v-if="src && !broken"
      :src="src"
      :alt="alt"
      class="h-full w-full object-cover"
      loading="lazy"
      decoding="async"
      @error="broken = true"
    />
    <span v-else class="select-none font-mono leading-none text-gray-300 dark:text-gray-500" :class="glyphClass">◈</span>
  </span>
</template>

<script setup lang="ts">
/**
 * 统一图标瓦片。兵种/升级图标可能来自两个地方：
 *   /icons/NN.png（wiki 已有的职业头像）或 /tech-icons/<btn-*.png>（从地图/CASC 转出来的按钮图）。
 * 加载失败时降级成 ◈ 占位，不裂图。
 */
const props = withDefaults(defineProps<{
  icon?: string | null
  alt?: string
  size?: 'xs' | 'sm' | 'md' | 'lg'
}>(), { size: 'sm', alt: '' })

const broken = ref(false)
watch(() => props.icon, () => { broken.value = false })

const src = computed(() => {
  const i = props.icon
  if (!i) return ''
  return i.startsWith('/') ? i : `/tech-icons/${i}`
})

const SIZES: Record<string, [string, string]> = {
  xs: ['h-4 w-4', 'text-[0.5rem]'],
  sm: ['h-6 w-6', 'text-[0.6rem]'],
  md: ['h-11 w-11', 'text-base'],
  lg: ['h-16 w-16', 'text-xl'],
}
const sizeClass = computed(() => SIZES[props.size][0])
const glyphClass = computed(() => SIZES[props.size][1])
</script>
