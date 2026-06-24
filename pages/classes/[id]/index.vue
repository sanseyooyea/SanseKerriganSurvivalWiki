<template>
  <div v-if="cls">
    <!-- Breadcrumb -->
    <NuxtLink to="/classes"
      class="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-gray-600 transition-colors mb-6">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
      职业列表
    </NuxtLink>

    <!-- Hero Header -->
    <div class="wiki-card p-6 mb-6 stagger-item">
      <div class="flex items-start gap-5">
        <div class="relative">
          <img :src="`/icons/${String(cls.id).padStart(2, '0')}.png`"
            :alt="cls.nameEn"
            class="w-20 h-20 rounded-xl shadow-card" />
          <div :class="teamDot" class="absolute -bottom-1 -right-1 w-5 h-5 rounded-full border-2 border-white dark:border-gray-800 shadow-sm"></div>
        </div>
        <div class="flex-1">
          <div class="flex items-center justify-between mb-1">
            <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 tracking-tight">
              {{ cls.nameZh || cls.nameEn }}
            </h1>
            <NuxtLink v-if="canEdit" :to="`/classes/${cls.id}/edit`"
              class="px-3 py-1.5 text-xs font-medium text-survivor-700 dark:text-survivor-300 border border-survivor-300 dark:border-survivor-700 rounded-lg hover:bg-survivor-50 dark:hover:bg-survivor-900/30 transition">
              编辑
            </NuxtLink>
          </div>
          <div class="text-sm text-gray-400 dark:text-gray-500 mb-2">{{ cls.nameEn }}</div>
          <div class="flex gap-2">
            <span :class="teamBadgeClass" class="text-xs px-2.5 py-1 rounded-md font-medium">
              {{ cls.team === 'Kerrigan' ? '凯瑞甘' : '生存者' }}
            </span>
            <span class="text-xs px-2.5 py-1 rounded-md bg-surface-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 font-medium">
              {{ categoryLabel }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Win rate -->
    <NuxtLink v-if="balance && balance.plays > 0" to="/balance"
      class="wiki-card p-4 mb-6 flex items-center gap-4 hover:shadow-card-hover transition group"
      :class="{ 'opacity-60': balance.low_sample }">
      <div class="flex flex-col">
        <span class="text-xs text-gray-500 dark:text-gray-400">官方胜率</span>
        <span class="text-2xl font-mono font-bold"
          :class="(balance.win_rate ?? 0) >= 0.5 ? 'text-green-600' : 'text-red-500'">
          {{ balance.win_rate == null ? '—' : (balance.win_rate * 100).toFixed(1) + '%' }}
        </span>
      </div>
      <div class="flex-1">
        <div class="h-2 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
          <div class="h-full rounded-full" :class="cls.team === 'Kerrigan' ? 'wr-bar-k' : 'wr-bar-s'"
            :style="`width: ${Math.min((balance.win_rate ?? 0) * 100, 100)}%`" />
        </div>
        <div class="mt-1.5 flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
          <span>{{ balance.plays.toLocaleString() }} 场样本</span>
          <span v-if="balance.low_sample" class="text-amber-500">· 样本不足，仅供参考</span>
        </div>
      </div>
      <svg class="w-4 h-4 text-gray-300 dark:text-gray-600 group-hover:text-survivor-500 transition" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7"/>
      </svg>
    </NuxtLink>

    <!-- Stats Panel (unified) -->
    <div class="wiki-card p-5 mb-6">
      <div class="section-title">属性与成长</div>
      <table class="w-full text-sm">
        <thead>
          <tr class="text-xs text-gray-500 dark:text-gray-400">
            <th class="text-left font-medium pb-2 pl-1">属性</th>
            <th class="text-right font-medium pb-2">基础值</th>
            <th class="text-right font-medium pb-2 pr-1">每级</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
          <tr v-if="cls.stats.hp">
            <td class="py-2 pl-1 text-gray-700 dark:text-gray-300">生命值</td>
            <td class="py-2 text-right font-mono font-semibold text-gray-900 dark:text-gray-100">{{ cls.stats.hp.toLocaleString() }}</td>
            <td class="py-2 pr-1 text-right font-mono text-red-600 dark:text-red-400">
              {{ cls.team === 'Kerrigan' ? '固定' : (vet ? attrBonus.hp : '') }}
            </td>
          </tr>
          <tr v-if="cls.stats.speed">
            <td class="py-2 pl-1 text-gray-700 dark:text-gray-300">
              移动速度
            </td>
            <td class="py-2 text-right font-mono font-semibold text-gray-900 dark:text-gray-100">
              {{ cls.stats.speed }}
              <span v-if="cls.team === 'Kerrigan'" class="text-xs font-normal text-green-600 dark:text-green-400 ml-1">
                ({{ (cls.stats.speed * 1.3).toFixed(2) }} 菌毯)
              </span>
            </td>
            <td class="py-2 pr-1 text-right font-mono text-green-600 dark:text-green-400">{{ vet ? attrBonus.speed : '' }}</td>
          </tr>
          <tr v-if="cls.stats.armor != null">
            <td class="py-2 pl-1 text-gray-700 dark:text-gray-300">护甲</td>
            <td class="py-2 text-right font-mono font-semibold text-gray-900 dark:text-gray-100">{{ cls.stats.armor }}</td>
            <td class="py-2 pr-1 text-right font-mono text-red-600 dark:text-red-400">{{ vet ? attrBonus.armor : '' }}</td>
          </tr>
          <tr v-if="cls.stats.damage">
            <td class="py-2 pl-1 text-gray-700 dark:text-gray-300">
              攻击伤害
              <span v-if="cls.stats.attackCount > 1" class="text-xs text-gray-400 dark:text-gray-500">x{{ cls.stats.attackCount }}</span>
            </td>
            <td class="py-2 text-right font-mono font-semibold text-gray-900 dark:text-gray-100">{{ cls.stats.damage }}</td>
            <td class="py-2 pr-1 text-right font-mono text-red-600 dark:text-red-400">{{ vet ? attrBonus.damage : '' }}</td>
          </tr>
          <tr v-if="cls.stats.attackSpeed">
            <td class="py-2 pl-1 text-gray-700 dark:text-gray-300">攻击间隔</td>
            <td class="py-2 text-right font-mono font-semibold text-gray-900 dark:text-gray-100">{{ cls.stats.attackSpeed }}s</td>
            <td class="py-2 pr-1 text-right font-mono text-green-600 dark:text-green-400">{{ vet ? attrBonus.atkSpeed : '' }}</td>
          </tr>
          <tr v-if="cls.stats.energy">
            <td class="py-2 pl-1 text-gray-700 dark:text-gray-300">能量</td>
            <td class="py-2 text-right font-mono font-semibold text-gray-900 dark:text-gray-100">{{ cls.stats.energy }}</td>
            <td class="py-2 pr-1 text-right font-mono text-blue-600 dark:text-blue-400">{{ vet ? attrBonus.energy : '' }}</td>
          </tr>
          <tr v-if="cls.stats.energyRegen">
            <td class="py-2 pl-1 text-gray-700 dark:text-gray-300">能量恢复</td>
            <td class="py-2 text-right font-mono font-semibold text-gray-900 dark:text-gray-100">{{ cls.stats.energyRegen }}/s</td>
            <td class="py-2 pr-1 text-right font-mono text-blue-600 dark:text-blue-400">{{ vet ? attrBonus.energyRegen : '' }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="vet" class="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
        <div class="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
          <span>每级成长：</span>
          <span class="font-mono"><span class="text-red-600 dark:text-red-400 font-semibold">{{ vet.str }}</span> 力量</span>
          <span class="font-mono"><span class="text-green-600 dark:text-green-400 font-semibold">{{ vet.agi }}</span> 敏捷</span>
          <span class="font-mono"><span class="text-blue-600 dark:text-blue-400 font-semibold">{{ vet.int }}</span> 智力</span>
        </div>
        <div class="mt-2 text-xs text-gray-400 dark:text-gray-500 leading-relaxed">
          <template v-if="cls.team === 'Kerrigan'">
            力量：近战+8%/远程+4%/护甲+0.5 · 敏捷：移速+0.035/攻速+6% · 智力：法伤+5%/能量+4%/回能+0.039/s
          </template>
          <template v-else>
            力量：近战+7%/远程+3%/生命+2% · 敏捷：移速+0.031/攻速+3% · 智力：法伤+10%/能量+3%/回能+0.0312/s
          </template>
        </div>
      </div>
    </div>

    <!-- Abilities Section -->
    <div class="wiki-card p-5 mb-6">
      <div class="section-title">技能 · {{ displayAbilities.length }}</div>
      <div class="space-y-2">
        <AbilityCard v-for="aid in displayAbilities" :key="aid" :ability-id="aid" />
      </div>
    </div>

    <!-- Units Section -->
    <div v-if="displayUnits.troops.length" class="wiki-card p-5 mb-6">
      <div class="section-title">兵种 · {{ displayUnits.troops.length }}</div>
      <div class="space-y-2">
        <UnitCard v-for="unit in displayUnits.troops" :key="unit.id || unit.nameZh" :unit="unit" />
      </div>
    </div>

    <!-- Buildings Section -->
    <div v-if="displayUnits.buildings.length" class="wiki-card p-5 mb-6">
      <div class="section-title">建筑 · {{ displayUnits.buildings.length }}</div>
      <div class="space-y-2">
        <UnitCard v-for="unit in displayUnits.buildings" :key="unit.id || unit.nameZh" :unit="unit" :is-building="true" />
      </div>
    </div>

    <!-- Economy Section -->
    <div v-if="displayUnits.economy.length" class="wiki-card p-5 mb-6">
      <div class="section-title">经济建筑 · {{ displayUnits.economy.length }}</div>
      <div class="space-y-2">
        <UnitCard v-for="unit in displayUnits.economy" :key="unit.id || unit.nameZh" :unit="unit" :is-building="true" />
      </div>
    </div>

    <!-- Description Section -->
    <div v-if="displayDesc" class="wiki-card p-5 mb-6">
      <div class="section-title">职业描述</div>
      <div class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed" v-html="parsedDesc" />
    </div>

    <!-- User Notes Section -->
    <div v-if="renderedNotes" class="wiki-card p-5 mb-6">
      <div class="section-title">社区攻略</div>
      <div class="prose prose-sm dark:prose-invert max-w-none" v-html="renderedNotes" />
    </div>
  </div>

  <div v-else class="text-center py-20 text-gray-400">
    <p class="text-lg">职业未找到</p>
    <NuxtLink to="/classes" class="text-sm text-survivor-600 hover:underline mt-2 inline-block">
      返回职业列表
    </NuxtLink>
  </div>
</template>

<script setup lang="ts">
import { marked } from 'marked'
import DOMPurify from 'isomorphic-dompurify'

const route = useRoute()
const { canEdit } = useAuth()
const { getById } = useClassData()
const { getForHero } = useVeterancyData()
const { getForHero: getUnitsForHero } = useUnitData()
const { getByRoleId } = useBalanceData()

const cls = computed(() => getById(Number(route.params.id)))
const balance = computed(() => getByRoleId(Number(route.params.id)))
const vet = computed(() => cls.value ? getForHero(cls.value.nameEn) : undefined)
const heroUnits = computed(() => cls.value ? getUnitsForHero(cls.value.nameEn) : { troops: [], buildings: [], economy: [] })

const attrBonus = computed(() => {
  if (!vet.value || !cls.value) return {}
  const v = vet.value
  const isK = cls.value.team === 'Kerrigan'
  const speedPerAgi = isK ? 0.0351 : 0.0312
  const atkSpeedPct = isK ? 6 : 3
  const hpPctPerStr = isK ? 0 : 2
  const armorPerStr = isK ? 0.5 : 0
  const meleePct = isK ? 8 : 7
  const energyRegenPerInt = isK ? 0.039 : 0.0312
  return {
    hp: hpPctPerStr ? `+${(v.str * hpPctPerStr)}%/级` : '',
    speed: `+${(v.agi * speedPerAgi).toFixed(2)}/级`,
    armor: armorPerStr ? `+${(v.str * armorPerStr).toFixed(1)}/级` : '-',
    damage: `+${v.str * meleePct}%/级`,
    atkSpeed: `+${v.agi * atkSpeedPct}%/级`,
    energy: `+${v.int * (isK ? 4 : 3)}%/级`,
    energyRegen: `+${(v.int * energyRegenPerInt).toFixed(4)}/s/级`,
  }
})

const teamDot = computed(() =>
  cls.value?.team === 'Kerrigan' ? 'bg-kerrigan-500' : 'bg-survivor-500'
)

const teamBadgeClass = computed(() =>
  cls.value?.team === 'Kerrigan'
    ? 'bg-kerrigan-50 text-kerrigan-700 border border-kerrigan-200 dark:bg-kerrigan-800/30 dark:text-kerrigan-200 dark:border-kerrigan-700'
    : 'bg-survivor-50 text-survivor-700 border border-survivor-200 dark:bg-survivor-800/30 dark:text-survivor-200 dark:border-survivor-700'
)

const categoryMap: Record<string, string> = {
  Hunter: '猎手', Builder: '建造者', Support: '辅助',
  Defender: '防御者', Random: '随机'
}
const categoryLabel = computed(() =>
  categoryMap[cls.value?.category || ''] || cls.value?.category
)

const { data: override } = await useFetch(`/api/classes/${route.params.id}`)

// 双轨制：description/notes 取在线编辑的 override（文案，维护员可改）；
// 技能、兵种/建筑等结构化数据只读 git base（与地图绑定，不接受在线覆盖）。
const displayDesc = computed(() => override.value?.description || cls.value?.description)
const parsedDesc = computed(() =>
  displayDesc.value ? parseDescription(displayDesc.value) : ''
)

const displayAbilities = computed(() => cls.value?.abilities || [])

const displayUnits = computed(() => heroUnits.value)

const renderedNotes = computed(() => {
  const notes = override.value?.notes
  if (!notes) return ''
  return DOMPurify.sanitize(marked.parse(notes) as string)
})
</script>

<style scoped>
/* 胜率进度条颜色用 scoped CSS，避免 Tailwind 动态 class 被 purge */
.wr-bar-s { background: linear-gradient(90deg, #3b82f6, #2563eb); }
.wr-bar-k { background: linear-gradient(90deg, #ef4444, #dc2626); }
:global(.dark) .wr-bar-s { background: linear-gradient(90deg, #60a5fa, #3b82f6); }
:global(.dark) .wr-bar-k { background: linear-gradient(90deg, #f87171, #ef4444); }
</style>