<template>
  <div v-if="hero">
    <!-- 说明 -->
    <p v-if="showIntro" class="text-xs text-gray-500 dark:text-gray-400 mb-3 leading-relaxed">
      可在<span class="font-medium text-gray-600 dark:text-gray-300">研究建筑</span>处解锁的科技升级。多级科技逐级研究，
      每级成本（晶矿 / 气体）与研究时间独立；效果说明中的数值已代入地图实际数据。
    </p>

    <!-- 按分类分区 -->
    <div class="space-y-5">
      <div v-for="grp in groups" :key="grp.category ?? 'misc'">
        <div class="flex items-center gap-2 mb-2.5">
          <span class="inline-block px-2 py-0.5 rounded text-xs font-semibold"
            :class="badgeClass(grp.category)">{{ grp.label }}</span>
          <span class="text-xs text-gray-400 dark:text-gray-500">{{ grp.upgrades.length }} 项</span>
        </div>

        <!-- 图标磁贴·行：左侧大图标，右侧名称 + 逐级数值 -->
        <div class="space-y-1">
          <div v-for="u in grp.upgrades" :key="u.id"
            class="flex gap-3 px-2.5 py-2 rounded-lg hover:bg-surface-50 dark:hover:bg-gray-800/40 transition-colors">
            <!-- 图标磁贴 -->
            <div class="w-11 h-11 shrink-0 rounded-md overflow-hidden bg-gray-100 dark:bg-gray-800 ring-1 ring-black/5 dark:ring-white/10 flex items-center justify-center">
              <img v-if="u.icon" :src="`/tech-icons/${u.icon}`" :alt="u.nameZh"
                class="w-full h-full object-cover" loading="lazy" @error="onIconError" />
              <span v-else class="text-gray-300 dark:text-gray-600 text-base">◈</span>
            </div>

            <!-- 主体 -->
            <div class="flex-1 min-w-0">
              <!-- 名称 + 级数 -->
              <div class="flex items-center gap-2 mb-1">
                <span class="text-sm font-semibold text-gray-800 dark:text-gray-100">{{ u.nameZh }}</span>
                <span v-if="u.levels.length > 1"
                  class="font-mono text-[0.6rem] px-1.5 py-px rounded-full bg-survivor-50 text-survivor-600 dark:bg-survivor-900/30 dark:text-survivor-400">
                  {{ u.levels.length }} 级
                </span>
              </div>

              <!-- 单级：一行内联 -->
              <div v-if="u.levels.length === 1" class="flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 text-xs">
                <span class="font-mono shrink-0" v-html="costHtml(u.levels[0])"></span>
                <span v-if="u.levels[0].time" class="font-mono text-gray-400 dark:text-gray-500 shrink-0">{{ u.levels[0].time }}s</span>
                <span class="text-gray-600 dark:text-gray-300 whitespace-pre-line leading-relaxed">{{ u.levels[0].descZh || '—' }}</span>
              </div>

              <!-- 多级：逐级堆叠 -->
              <div v-else class="space-y-1">
                <div v-for="lv in u.levels" :key="lv.level"
                  class="flex gap-2 text-xs items-baseline">
                  <span class="font-mono text-[0.65rem] text-survivor-500 dark:text-survivor-400 w-4 shrink-0 text-right tabular-nums">{{ lv.level }}</span>
                  <span class="font-mono shrink-0 w-32 tabular-nums">
                    <span v-html="costHtml(lv)"></span><span v-if="lv.time" class="text-gray-400 dark:text-gray-500"> · {{ lv.time }}s</span>
                  </span>
                  <span class="text-gray-600 dark:text-gray-300 flex-1 min-w-0 whitespace-pre-line leading-relaxed">{{ lv.descZh || '—' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 秋伊专属：小进化（Chewolution）—— galaxy 驱动，与研究科技树独立，英文说明 -->
    <div v-if="hero.chewolution && hero.chewolution.length" class="mt-6">
      <div class="flex items-center gap-2 mb-2">
        <span class="inline-block px-2 py-0.5 rounded text-xs font-semibold bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300">小进化 Chewolution</span>
        <span class="text-xs text-gray-400 dark:text-gray-500">{{ hero.chewolution.length }} 项 · 升级时可选</span>
      </div>
      <p class="text-xs text-gray-500 dark:text-gray-400 mb-2 leading-relaxed">
        秋伊在提升等级时可选择的次要强化，可多次堆叠至上限，与上方研究科技树相互独立。（地图仅提供英文说明）
      </p>
      <div class="grid gap-1.5 sm:grid-cols-2">
        <div v-for="c in hero.chewolution" :key="c.index"
          class="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-surface-50/50 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-700/60">
          <span class="text-xs text-gray-600 dark:text-gray-300 flex-1 min-w-0">{{ c.descEn }}</span>
          <span class="font-mono text-[0.65rem] text-gray-400 dark:text-gray-500 shrink-0">×{{ c.maxCount }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 单个英雄的科技研究渲染器：/classes/[id] 科技板块使用。对称 HeroEconomy.vue。
const props = withDefaults(defineProps<{ name: string; showIntro?: boolean }>(), {
  showIntro: true,
})

const { getTech, getTechGroups } = useTechData()

const hero = computed(() => getTech(props.name))
const groups = computed(() => getTechGroups(props.name))

// 分类徽章配色：静态完整 class 串映射（避免 Tailwind purge 丢样式）。
const BADGE: Record<string, string> = {
  AttackBonus: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  ArmorBonus: 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300',
  SpellResearch: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
  Talents: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
}
const BADGE_FALLBACK = 'bg-gray-100 text-gray-600 dark:bg-gray-700/50 dark:text-gray-300'
function badgeClass(cat: string | null) {
  return (cat && BADGE[cat]) || BADGE_FALLBACK
}

// 成本内联渲染：晶矿灰 + 气体绿（数值均来自 tech.json，无用户输入，v-html 安全）。
function costHtml(lv: { cost: number; gasCost: number }) {
  const parts: string[] = []
  if (lv.cost) parts.push(`<span class="text-gray-600 dark:text-gray-300">${lv.cost}</span><span class="text-gray-400 dark:text-gray-500">矿</span>`)
  if (lv.gasCost) parts.push(`<span class="text-green-600 dark:text-green-400">${lv.gasCost}气</span>`)
  return parts.length ? parts.join(' ') : '<span class="text-gray-400 dark:text-gray-500">免费</span>'
}

// 图标缺失/未转换时优雅降级：隐藏 <img>，图标磁贴回落到占位符 ◈
function onIconError(e: Event) {
  const el = e.target as HTMLImageElement
  el.style.display = 'none'
  const tile = el.parentElement
  if (tile && !tile.querySelector('.icon-fallback')) {
    const span = document.createElement('span')
    span.className = 'icon-fallback text-gray-300 dark:text-gray-600 text-base'
    span.textContent = '◈'
    tile.appendChild(span)
  }
}
</script>
