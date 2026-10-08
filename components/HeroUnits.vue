<template>
  <div v-if="hero">
    <p v-if="showIntro" class="text-xs text-gray-500 dark:text-gray-400 mb-3 leading-relaxed">
      本职业可从<span class="font-medium text-gray-600 dark:text-gray-300">生产树</span>获得的所有单位。数值取自地图实际数据：
      DPS 分「对轻甲 / 对重甲 / 对凯瑞甘」三种靶标（凯瑞甘方为本图最高威胁目标）；
      升级曲线按该单位能吃到的研究科技逐级叠加（0 级 → 满级）。
      地图里无法静态解析的效果会标注「未解析」，不做估算。
    </p>

    <!-- 单位表格（按类别分区） -->
    <div class="space-y-5">
      <div v-for="grp in groups" :key="grp.category">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-sm font-semibold text-gray-800 dark:text-gray-200">{{ grp.label }}</span>
          <span class="text-xs text-gray-400 dark:text-gray-500">{{ grp.units.length }}</span>
        </div>
        <div class="space-y-1.5">
          <UnitRow v-for="u in grp.units" :key="u.id" :unit="u" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { UnitEntry } from '~/composables/useUnitsData'

const props = defineProps<{ name: string; showIntro?: boolean }>()
const { hasUnits, getHero, heroUnitEntries, groupByCategory } = useUnitsData()

const hero = computed(() => (hasUnits(props.name) ? getHero(props.name) : undefined))
const groups = computed(() => (hero.value ? groupByCategory(heroUnitEntries(props.name)) : []))
</script>
