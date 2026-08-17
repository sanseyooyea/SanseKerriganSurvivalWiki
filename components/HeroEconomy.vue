<template>
  <!-- 技术员 / 灵魂：独立自包含组件 -->
  <TechnicianEconomy v-if="isTechnician" />
  <SpiritEconomy v-else-if="isSpirit" />

  <!-- 常规 / 采集 / 挂件 / 装填 -->
  <div v-else-if="hero">
    <p v-if="showIntro && hero.incomeModel" class="text-xs text-gray-500 dark:text-gray-400 mb-3 leading-relaxed">{{ hero.incomeModel }}</p>

    <div v-if="heroChronos(hero).length" class="mb-3 px-3 py-2 rounded-lg bg-yellow-50/50 dark:bg-yellow-900/10 border border-yellow-100 dark:border-yellow-900/30">
      <div v-for="(c, i) in heroChronos(hero)" :key="i" class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-yellow-800 dark:text-yellow-300" :class="i > 0 ? 'mt-1.5 pt-1.5 border-t border-yellow-100 dark:border-yellow-800/50' : ''">
        <span>{{ c.name }}: <b class="font-mono">×{{ c.timeScale }}</b></span>
        <span>消耗: <b class="font-mono">{{ chronoCostLabel(c) }}</b></span>
        <span>持续: <b class="font-mono">{{ c.duration === 'permanent' ? '永久' : c.duration + 's' }}</b></span>
      </div>
    </div>

    <div v-if="!hero.harvestEconomy && !hero.addonEconomy && !hero.minerEconomy && !hero.extractionEconomy && !hero.farmEconomy" class="overflow-x-auto -mx-5 px-5">
      <table class="w-full text-sm min-w-[560px]">
        <thead>
          <tr class="text-xs text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-700">
            <th class="text-left font-medium pb-2 pl-1">建筑</th>
            <th class="text-right font-medium pb-2">收入</th>
            <th class="text-right font-medium pb-2">每秒</th>
            <th class="text-right font-medium pb-2">费用</th>
            <th class="text-right font-medium pb-2" title="购买1矿/秒收入所需的总投入（晶矿+气体），越低性价比越高">投资比</th>
            <th class="text-right font-medium pb-2">回本时间</th>
            <th v-if="heroChronos(hero).length" class="text-right font-medium pb-2 pr-1">加速回本</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50 dark:divide-gray-700/50">
          <tr v-for="b in hero.buildings" :key="b.id">
            <td class="py-2 pl-1 text-gray-700 dark:text-gray-300">
              {{ b.nameZh }}
              <span v-if="b.upgradeTo" class="text-xs text-gray-400"> →</span>
            </td>
            <td class="py-2 text-right font-mono font-semibold"
              :class="b.income ? 'text-green-600 dark:text-green-400' : 'text-gray-400'">
              {{ b.income ? `+${b.income}/${b.incomePeriod || '?'}s` : '-' }}
            </td>
            <td class="py-2 text-right font-mono text-emerald-600 dark:text-emerald-400">
              {{ incomePerSec(b) || '-' }}
            </td>
            <td class="py-2 text-right font-mono text-gray-600 dark:text-gray-300">
              <template v-if="b.cost != null">
                {{ b.cost }}<span v-if="b.gasCost" class="text-green-600 dark:text-green-500">+{{ b.gasCost }}g</span>
              </template>
              <template v-else>-</template>
            </td>
            <td class="py-2 text-right font-mono text-purple-600 dark:text-purple-400">
              {{ roi(b) || '-' }}
            </td>
            <td class="py-2 text-right font-mono text-blue-600 dark:text-blue-400">
              {{ paybackTime(b) || '-' }}
            </td>
            <td v-if="heroChronos(hero).length" class="py-2 pr-1 text-right font-mono text-yellow-600 dark:text-yellow-400">
              <span v-for="(c, i) in heroChronos(hero)" :key="i">
                <span v-if="i > 0"> / </span>{{ paybackTimeBoosted(b, c) || '-' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 采集型经济（塞兰迪斯）：矿区×探机 投资比矩阵 + 探机参数 -->
    <div v-if="hero.harvestEconomy" class="space-y-4">
      <!-- 投资比矩阵 -->
      <div class="overflow-x-auto -mx-5 px-5">
        <div class="text-xs font-semibold uppercase tracking-wider text-survivor-600 dark:text-survivor-400 mb-2">
          投资比矩阵 · 矿区 × 探机（数值越低越划算）
        </div>
        <table class="w-full text-sm min-w-[560px] border-separate border-spacing-1">
          <thead>
            <tr>
              <th class="text-left text-xs font-medium text-gray-500 dark:text-gray-400 pb-1 pl-1">矿区 \ 探机</th>
              <th v-for="p in hero.probes" :key="p.id" class="text-center text-xs font-medium text-gray-600 dark:text-gray-300 pb-1">
                {{ p.nameZh }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in hero.buildings" :key="b.id">
              <td class="py-1.5 pl-2 pr-3 rounded-lg bg-gray-50 dark:bg-gray-800/60 whitespace-nowrap">
                <span class="font-mono text-sm font-semibold text-gray-700 dark:text-gray-200">{{ b.nameZh }}</span>
                <span class="font-mono text-xs text-gray-400 dark:text-gray-500 ml-2">{{ b.cost }}矿 · +{{ b.income }}/趟</span>
              </td>
              <td v-for="p in hero.probes" :key="p.id"
                class="text-center rounded-lg bg-gray-50/60 dark:bg-gray-800/40">
                <div class="font-mono text-sm" :class="roiCellClass(b, p, hero.probes)">{{ harvestRoi(b, p) }}</div>
                <div class="font-mono text-[0.65rem] text-gray-400 dark:text-gray-500">{{ harvestPerSec(b, p).toFixed(0) }}/s</div>
              </td>
            </tr>
          </tbody>
        </table>
        <p class="text-xs text-gray-400 dark:text-gray-500 mt-2 leading-relaxed">
          投资比 =（矿区造价 + 探机造价）÷ 每秒采集量（买“1 矿/秒”持续收入的总投入，越低越划算）；下方小字为该组合每秒采集量。
          假设探机采集运回一趟基准 <b class="font-mono">0.1s</b>，实际每趟 = 0.1 × 探机耗时倍率。矿区最高 +16，无 +32。
          真实速率还受探机往返距离（地图布局）影响，此处为统一基准下的横向对比。
        </p>
      </div>

      <!-- 探机参数 -->
      <div>
        <div class="text-xs font-semibold uppercase tracking-wider text-survivor-600 dark:text-survivor-400 mb-2">
          采集探机 · 造价与参数
        </div>
        <div class="grid gap-2 sm:grid-cols-2">
          <div v-for="p in hero.probes" :key="p.id"
            class="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-100 dark:border-gray-700/60">
            <div class="flex-1 min-w-0">
              <div class="flex items-baseline gap-2">
                <span class="text-sm font-semibold text-gray-800 dark:text-gray-100">{{ p.nameZh }}</span>
                <span class="font-mono text-xs font-bold text-survivor-600 dark:text-survivor-400">{{ p.efficiency }}</span>
              </div>
              <div class="font-mono text-[0.7rem] text-gray-400 dark:text-gray-500 mt-0.5">
                采矿{{ p.mineTime }}s · 单趟量×{{ p.amountMult }}
              </div>
            </div>
            <div class="font-mono text-xs text-gray-600 dark:text-gray-300 shrink-0 text-right">
              <span v-if="p.cost">{{ p.cost }}矿</span><span v-if="p.cost && p.gasCost"> </span><span v-if="p.gasCost" class="text-green-600 dark:text-green-400">{{ p.gasCost }}气</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 挂件型经济（坦克）：建筑 × 挂件 回本/投资比矩阵 -->
    <div v-if="hero.addonEconomy" class="overflow-x-auto -mx-5 px-5">
      <div class="text-xs font-semibold uppercase tracking-wider text-survivor-600 dark:text-survivor-400 mb-2">
        挂件矩阵 · 经济建筑 × 挂件（投资比越低越划算）
      </div>
      <table class="w-full text-sm min-w-[560px] border-separate border-spacing-1">
        <thead>
          <tr>
            <th class="text-left text-xs font-medium text-gray-500 dark:text-gray-400 pb-1 pl-1">建筑 \ 挂件</th>
            <th v-for="col in addonCols" :key="col.key" class="text-center text-xs font-medium text-gray-600 dark:text-gray-300 pb-1">
              {{ col.label }}
              <span v-if="col.cost" class="block font-mono text-[0.6rem] text-gray-400 dark:text-gray-500 font-normal">+{{ col.cost }}矿<template v-if="col.gasCost">+{{ col.gasCost }}g</template></span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in hero.buildings" :key="b.id">
            <td class="py-1.5 pl-2 pr-3 rounded-lg bg-gray-50 dark:bg-gray-800/60 whitespace-nowrap">
              <span class="font-mono text-sm font-semibold text-gray-700 dark:text-gray-200">{{ b.nameZh }}</span>
              <span class="font-mono text-xs text-gray-400 dark:text-gray-500 ml-2">{{ b.cost }}矿 · {{ b.income }}/{{ b.incomePeriod }}s</span>
            </td>
            <td v-for="col in addonCols" :key="col.key"
              class="text-center rounded-lg bg-gray-50/60 dark:bg-gray-800/40">
              <div class="font-mono text-sm" :class="addonRoiCellClass(b, col)">{{ addonRoi(b, col) }}矿</div>
              <div class="font-mono text-[0.65rem] text-gray-400 dark:text-gray-500">
                {{ addonPerSec(b, col).toFixed(2) }}/s · {{ formatTime(addonPayback(b, col)) }}
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p class="text-xs text-gray-400 dark:text-gray-500 mt-2 leading-relaxed">
        每个经济建筑限挂一个挂件（科技实验室 / 反应堆，二选一）。
        投资比 =（建筑造价 + 挂件造价）÷ 每秒产矿（买"1 矿/秒"持续收入的总投入，越低越划算，仅计晶矿）；
        小字为每秒产矿与回本时间。挂件气体消耗见表头。
      </p>
    </div>

    <!-- 装填型经济（阿瑞斯）：矿区容器 + 工人产矿，货舱格数受限 -->
    <div v-if="hero.minerEconomy" class="space-y-4">
      <!-- 矿区容器 -->
      <div class="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-survivor-50/60 dark:bg-survivor-900/10 border border-survivor-100 dark:border-survivor-900/30">
        <div class="flex-1 min-w-0">
          <div class="flex items-baseline gap-2 flex-wrap">
            <span class="text-sm font-semibold text-survivor-700 dark:text-survivor-300">{{ hero.outpost.nameZh }}</span>
            <span class="font-mono text-xs font-bold text-survivor-600 dark:text-survivor-400">货舱 {{ hero.outpost.cargoSpace }} 格</span>
            <span v-if="hero.outpost.cargoUpgrade" class="font-mono text-[0.65rem] text-emerald-600 dark:text-emerald-400">升级后 {{ hero.outpost.cargoUpgrade.cargoSpace }} 格</span>
          </div>
          <div class="text-[0.7rem] text-gray-500 dark:text-gray-400 mt-0.5">{{ hero.outpost.notes }}</div>
          <div v-if="hero.outpost.cargoUpgrade" class="text-[0.7rem] text-gray-500 dark:text-gray-400 mt-0.5">
            <span class="text-emerald-600 dark:text-emerald-400">{{ hero.outpost.cargoUpgrade.nameZh }}</span>：货舱扩至 {{ hero.outpost.cargoUpgrade.cargoSpace }} 格 ·
            {{ hero.outpost.cargoUpgrade.cost }}矿<template v-if="hero.outpost.cargoUpgrade.gasCost">+{{ hero.outpost.cargoUpgrade.gasCost }}气</template> · 研究 {{ hero.outpost.cargoUpgrade.researchTime }}s
          </div>
        </div>
        <div class="font-mono text-xs text-gray-600 dark:text-gray-300 shrink-0 text-right">
          {{ hero.outpost.cost }}矿<template v-if="hero.outpost.gasCost">+{{ hero.outpost.gasCost }}g</template>
          <span class="block text-[0.65rem] text-gray-400">建造 {{ hero.outpost.buildTime }}s</span>
        </div>
      </div>

      <!-- 工人对比表 -->
      <div class="overflow-x-auto -mx-5 px-5">
        <div class="text-xs font-semibold uppercase tracking-wider text-survivor-600 dark:text-survivor-400 mb-2">
          工人 · 产矿与货舱效率
        </div>
        <table class="w-full text-sm min-w-[560px]">
          <thead>
            <tr class="text-left text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-700/60">
              <th class="font-medium pb-2">工人</th>
              <th class="text-right font-medium pb-2 pr-1">产矿</th>
              <th class="text-right font-medium pb-2 pr-1">每秒</th>
              <th class="text-right font-medium pb-2 pr-1">造价</th>
              <th class="text-right font-medium pb-2 pr-1">占格</th>
              <th class="text-right font-medium pb-2 pr-1">每格效率</th>
              <th class="text-right font-medium pb-2 pr-1">回本</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50 dark:divide-gray-800/60">
            <tr v-for="m in hero.miners" :key="m.id">
              <td class="py-2 font-medium text-gray-800 dark:text-gray-100">{{ m.nameZh }}</td>
              <td class="py-2 pr-1 text-right font-mono text-gray-600 dark:text-gray-300">+{{ m.income }}/{{ m.incomePeriod }}s</td>
              <td class="py-2 pr-1 text-right font-mono text-gray-600 dark:text-gray-300">{{ minerPerSec(m).toFixed(2) }}</td>
              <td class="py-2 pr-1 text-right font-mono">
                {{ m.cost }}<span v-if="m.gasCost" class="text-green-600 dark:text-green-500">+{{ m.gasCost }}g</span>
              </td>
              <td class="py-2 pr-1 text-right font-mono text-gray-500 dark:text-gray-400">{{ m.cargoSize }}</td>
              <td class="py-2 pr-1 text-right font-mono font-semibold" :class="minerPerSpaceCellClass(m, hero.miners)">{{ minerPerSpace(m).toFixed(2) }}/s</td>
              <td class="py-2 pr-1 text-right font-mono text-gray-600 dark:text-gray-300">{{ formatTime(minerPayback(m)) }}</td>
            </tr>
          </tbody>
        </table>
        <p class="text-xs text-gray-400 dark:text-gray-500 mt-2 leading-relaxed">
          工人装入矿区后按其等级周期性产矿。<b>每格效率</b> = 每秒产矿 ÷ 占格数 ——矿区货舱有限，故它才是真正的优化指标：等级越高越省格（H 级为 A 级的 10 倍）。
          三档工人的<b>矿物回本</b>都恰好 100 秒，差别只在货舱效率与气体消耗。
          满编方案：{{ hero.outpost.cargoSpace }} 格塞 1 名 H 级 + 1 名 B 级 = <b class="font-mono text-survivor-600 dark:text-survivor-400">12 矿/秒</b>；升级到 {{ hero.outpost.cargoUpgrade?.cargoSpace }} 格后可塞 2 名 H 级 = <b class="font-mono text-emerald-600 dark:text-emerald-400">20 矿/秒</b>（单矿区上限）。
        </p>
      </div>

      <!-- 工人通道 -->
      <div class="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-100 dark:border-gray-700/60">
        <div class="flex-1 min-w-0">
          <div class="text-sm font-semibold text-gray-800 dark:text-gray-100">{{ hero.tunnel.nameZh }}</div>
          <div class="text-[0.7rem] text-gray-500 dark:text-gray-400 mt-0.5">{{ hero.tunnel.notes }}</div>
        </div>
        <div class="font-mono text-xs text-gray-600 dark:text-gray-300 shrink-0 text-right">
          {{ hero.tunnel.cost }}矿<template v-if="hero.tunnel.gasCost">+{{ hero.tunnel.gasCost }}g</template>
          <span class="block text-[0.65rem] text-gray-400">建造 {{ hero.tunnel.buildTime }}s</span>
        </div>
      </div>
    </div>

    <!-- 萃取型经济（先知）：无自有收入建筑，结界寄生盟友/自身经济建筑的原始收入 -->
    <div v-if="hero.extractionEconomy && hero.extraction" class="space-y-4">
      <!-- 结界参数速览 -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div class="px-3 py-2 rounded-lg bg-indigo-50/70 dark:bg-indigo-900/15 border border-indigo-100 dark:border-indigo-900/30">
          <div class="text-[0.65rem] text-gray-500 dark:text-gray-400">萃取效率</div>
          <div class="font-mono text-sm font-semibold text-indigo-700 dark:text-indigo-300">
            {{ Math.round(hero.extraction.efficiencyBase * 100) }}%
            <span class="text-emerald-600 dark:text-emerald-400">→ {{ Math.round(hero.extraction.efficiencyUpgraded * 100) }}%</span>
          </div>
          <div class="text-[0.6rem] text-gray-400 dark:text-gray-500">{{ hero.extraction.upgradeName }}后</div>
        </div>
        <div class="px-3 py-2 rounded-lg bg-indigo-50/70 dark:bg-indigo-900/15 border border-indigo-100 dark:border-indigo-900/30">
          <div class="text-[0.65rem] text-gray-500 dark:text-gray-400">萃取范围</div>
          <div class="font-mono text-sm font-semibold text-indigo-700 dark:text-indigo-300">
            {{ hero.extraction.rangeBase }}
            <span class="text-emerald-600 dark:text-emerald-400">→ {{ hero.extraction.rangeUpgraded }}</span>
          </div>
          <div class="text-[0.6rem] text-gray-400 dark:text-gray-500">{{ hero.extraction.upgradeName }}后</div>
        </div>
        <div class="px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-100 dark:border-gray-700/60">
          <div class="text-[0.65rem] text-gray-500 dark:text-gray-400">结算周期</div>
          <div class="font-mono text-sm font-semibold text-gray-700 dark:text-gray-200">{{ hero.extraction.incomePeriod }}s</div>
          <div class="text-[0.6rem] text-gray-400 dark:text-gray-500">最多叠 {{ hero.extraction.maxStacks }} 层</div>
        </div>
        <div class="px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-100 dark:border-gray-700/60">
          <div class="text-[0.65rem] text-gray-500 dark:text-gray-400">{{ hero.extraction.wardNameZh }}（上限 {{ hero.extraction.wardCap }}）</div>
          <div class="font-mono text-sm font-semibold text-gray-700 dark:text-gray-200">
            {{ hero.extraction.wardHp }}<span class="text-blue-500">+{{ hero.extraction.wardShields }}盾</span>
          </div>
          <div class="text-[0.6rem] text-gray-400 dark:text-gray-500">无矿物造价</div>
        </div>
      </div>

      <!-- 萃取收益速查表 -->
      <div class="overflow-x-auto -mx-5 px-5">
        <div class="text-xs font-semibold uppercase tracking-wider text-survivor-600 dark:text-survivor-400 mb-2">
          萃取收益速查 · 按目标建筑原始收入
        </div>
        <table class="w-full text-sm min-w-[560px]">
          <thead>
            <tr class="text-xs text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-700">
              <th class="text-left font-medium pb-2 pl-1">目标建筑（原始收入）</th>
              <th class="text-right font-medium pb-2">每次萃取</th>
              <th class="text-right font-medium pb-2">每秒</th>
              <th class="text-right font-medium pb-2">强化后每次</th>
              <th class="text-right font-medium pb-2 pr-1">强化后每秒</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50 dark:divide-gray-700/50">
            <tr v-for="ex in hero.extraction.examples" :key="ex.raw">
              <td class="py-2 pl-1 text-gray-700 dark:text-gray-300">
                <span class="font-medium">{{ ex.label }}</span>
                <span class="text-xs text-gray-400 dark:text-gray-500 ml-1">{{ ex.eg }} · 原始 {{ ex.raw }}</span>
              </td>
              <td class="py-2 text-right font-mono text-gray-600 dark:text-gray-300">{{ siphonTick(ex.raw, hero.extraction.efficiencyBase) }}</td>
              <td class="py-2 text-right font-mono text-emerald-600 dark:text-emerald-400">{{ siphonSec(ex.raw, hero.extraction.efficiencyBase, hero.extraction.incomePeriod) }}/s</td>
              <td class="py-2 text-right font-mono text-gray-600 dark:text-gray-300">{{ siphonTick(ex.raw, hero.extraction.efficiencyUpgraded) }}</td>
              <td class="py-2 pr-1 text-right font-mono font-semibold text-emerald-600 dark:text-emerald-400">{{ siphonSec(ex.raw, hero.extraction.efficiencyUpgraded, hero.extraction.incomePeriod) }}/s</td>
            </tr>
          </tbody>
        </table>
        <p class="text-xs text-gray-400 dark:text-gray-500 mt-2 leading-relaxed">
          {{ hero.extraction.note }}
          「每次萃取」= 原始收入 × 效率的期望值（不足 1 时按概率取整）；「每秒」= 每次 ÷ {{ hero.extraction.incomePeriod }}s（单层）。
          一座结界可同时萃取范围内的所有经济建筑，故实际收入是覆盖到的每座建筑之和；叠满 {{ hero.extraction.maxStacks }} 层时对该建筑的萃取再 ×{{ hero.extraction.maxStacks }}。
        </p>
      </div>
    </div>

    <!-- 击杀farming型经济（元素使）：无经济建筑，收入来自击杀赏金/农场叠层/护盾/存款，全部需高血量 -->
    <div v-if="hero.farmEconomy && hero.farm" class="space-y-4">
      <!-- 收入门槛警示 -->
      <div class="px-3 py-2 rounded-lg bg-red-50/70 dark:bg-red-900/15 border border-red-100 dark:border-red-900/30">
        <div class="text-xs font-semibold text-red-700 dark:text-red-300">
          收入门槛：元素使血量必须 ≥ {{ hero.farm.healthGate }}%（护盾收入需满血 {{ hero.farm.shieldGate }}%）才结算
        </div>
        <div class="text-[0.7rem] text-red-600/80 dark:text-red-400/80 mt-0.5">掉血 / 破盾时 farming 与护盾收入立即中断——先保命保盾才有钱。</div>
      </div>

      <!-- 击杀赏金 -->
      <div>
        <div class="text-xs font-semibold uppercase tracking-wider text-survivor-600 dark:text-survivor-400 mb-2">击杀赏金 · 每次击杀</div>
        <div class="grid gap-2 sm:grid-cols-2">
          <div class="px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-100 dark:border-gray-700/60">
            <div class="text-[0.7rem] text-gray-500 dark:text-gray-400 mb-0.5">获得气体</div>
            <div class="font-mono text-sm text-green-600 dark:text-green-400">{{ hero.farm.bountyGas }}</div>
          </div>
          <div class="px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-100 dark:border-gray-700/60">
            <div class="text-[0.7rem] text-gray-500 dark:text-gray-400 mb-0.5">额外晶矿</div>
            <div class="font-mono text-sm text-emerald-600 dark:text-emerald-400">{{ hero.farm.bountyMineral }}</div>
          </div>
        </div>
      </div>

      <!-- 被动矿源：农场叠层 + 护盾 -->
      <div>
        <div class="text-xs font-semibold uppercase tracking-wider text-survivor-600 dark:text-survivor-400 mb-2">被动矿源 · 需维持血量</div>
        <div class="grid gap-2 sm:grid-cols-2">
          <div class="px-3 py-2.5 rounded-lg bg-survivor-50/60 dark:bg-survivor-900/10 border border-survivor-100 dark:border-survivor-900/30">
            <div class="flex items-baseline gap-2">
              <span class="text-sm font-semibold text-survivor-700 dark:text-survivor-300">农场叠层</span>
              <span class="font-mono text-xs font-bold text-survivor-600 dark:text-survivor-400">每层 +{{ hero.farm.stacks.perStack }} 矿 / {{ hero.farm.stacks.period }}s</span>
            </div>
            <div class="text-[0.7rem] text-gray-500 dark:text-gray-400 mt-0.5">
              击杀累积层数（上限 {{ hero.farm.stacks.capBase }}，{{ hero.farm.stacks.capNote }}），停手回落。
              满层 ≈ <b class="font-mono text-emerald-600 dark:text-emerald-400">{{ fmt(hero.farm.stacks.capBase * hero.farm.stacks.perStack / hero.farm.stacks.period) }} 矿/s</b>
            </div>
          </div>
          <div class="px-3 py-2.5 rounded-lg bg-blue-50/60 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30">
            <div class="flex items-baseline gap-2">
              <span class="text-sm font-semibold text-blue-700 dark:text-blue-300">护盾收入</span>
              <span class="font-mono text-xs font-bold text-blue-600 dark:text-blue-400">当前护盾 {{ hero.farm.shield.percent }}% / {{ hero.farm.shield.period }}s</span>
            </div>
            <div class="text-[0.7rem] text-gray-500 dark:text-gray-400 mt-0.5">
              需满血 {{ hero.farm.shieldGate }}%；Showtime 增益最多再叠 {{ hero.farm.shield.showtimeMax }} 层。护盾越高被动矿越多。
            </div>
          </div>
        </div>
      </div>

      <!-- 存款投资 -->
      <div class="overflow-x-auto -mx-5 px-5">
        <div class="text-xs font-semibold uppercase tracking-wider text-survivor-600 dark:text-survivor-400 mb-2">
          存款投资 (Stash) · 到期本金 ×{{ hero.farm.stash.payoffBase }}（+研究加成）
        </div>
        <table class="w-full text-sm min-w-[420px]">
          <thead>
            <tr class="text-xs text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-700">
              <th class="text-left font-medium pb-2 pl-1">存入本金</th>
              <th class="text-right font-medium pb-2">到期返还</th>
              <th class="text-right font-medium pb-2 pr-1">净收益</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50 dark:divide-gray-700/50">
            <tr v-for="t in hero.farm.stash.tiers" :key="t">
              <td class="py-2 pl-1 font-mono text-gray-700 dark:text-gray-300">{{ t.toLocaleString() }}</td>
              <td class="py-2 text-right font-mono text-emerald-600 dark:text-emerald-400">{{ (t * hero.farm.stash.payoffBase).toLocaleString() }}</td>
              <td class="py-2 pr-1 text-right font-mono text-purple-600 dark:text-purple-400">+{{ (t * (hero.farm.stash.payoffBase - 1)).toLocaleString() }}</td>
            </tr>
          </tbody>
        </table>
        <p class="text-xs text-gray-400 dark:text-gray-500 mt-2 leading-relaxed">
          把晶矿存入一个单位，到期若该单位仍存活则按上表返还（研究可提高倍率）；若该单位在到期前死亡，存款全部损失。高风险高回报的理财机制。
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 单个英雄的经济详情渲染器：/economy 手风琴面板与 /classes/[id] 经济板块共用。
// 数值算法逐字迁自原 pages/economy/index.vue，保证零回归。
const props = withDefaults(defineProps<{ name: string; showIntro?: boolean }>(), {
  showIntro: true,
})

const { getEconomy } = useEconomyData()

const isTechnician = computed(() => props.name === 'Technician')
const isSpirit = computed(() => props.name === 'Spirit')
const hero = computed(() => getEconomy(props.name))

function heroChronos(h: any): any[] {
  if (!h.chrono) return []
  return Array.isArray(h.chrono) ? h.chrono : [h.chrono]
}

function chronoCostLabel(chrono: any) {
  if (chrono.costLabel) return chrono.costLabel
  if (chrono.gasCost) return `${chrono.gasCost} 气体/次`
  if (chrono.energyCost > 0) return `${chrono.energyCost} 能量`
  return '无'
}

function incomePerSec(b: any) {
  if (!b.income || !b.incomePeriod) return null
  const ips = b.income / b.incomePeriod
  return `${ips % 1 === 0 ? ips : ips.toFixed(2)}/s`
}

function roi(b: any) {
  if (!b.income || !b.incomePeriod || b.cost == null) return null
  const ips = b.income / b.incomePeriod
  const totalCost = b.cost + (b.gasCost || 0)
  const costPer1ps = Math.round(totalCost / ips)
  return `${costPer1ps}矿`
}

function paybackTime(b: any) {
  if (!b.income || !b.cost || !b.incomePeriod) return null
  const incomePerSec = b.income / b.incomePeriod
  const seconds = Math.round(b.cost / incomePerSec)
  return formatTime(seconds)
}

function paybackTimeBoosted(b: any, chrono: any) {
  if (!b.income || !b.cost || !b.incomePeriod || !chrono) return null
  const incomePerSec = (b.income / b.incomePeriod) * chrono.timeScale
  const seconds = Math.round(b.cost / incomePerSec)
  return formatTime(seconds)
}

function formatTime(seconds: number) {
  if (seconds >= 60) {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return s > 0 ? `${m}m${s}s` : `${m}m`
  }
  return `${seconds}s`
}

// —— 先知萃取经济 ——
// 结界每 period 秒萃取范围内每座经济建筑「原始收入 × 效率」的期望值（不足 1 按概率取整）。
function fmt(n: number) {
  return n % 1 === 0 ? String(n) : n.toFixed(2).replace(/\.?0+$/, '')
}
function siphonTick(raw: number, eff: number) {
  return fmt(raw * eff)
}
function siphonSec(raw: number, eff: number, period: number) {
  return fmt((raw * eff) / period)
}

// —— 塞兰迪斯采集经济 ——
// 一趟 = 采矿 + 运输往返。
//   采矿耗时 = 探机各自的固定采矿时间（游戏实测：普通2.5s / 高级·专家·普罗比斯1.5s）
//   运输往返 = 0.1s（完成采矿到运回基地）
//   每秒采集 = 矿区单趟量 × 单趟量倍率 ÷ 一趟总时长
const TRIP_TRANSPORT = 0.1  // 运输往返(s)

function tripTime(probe: any) {
  return (probe.mineTime || 0) + TRIP_TRANSPORT
}
function harvestPerSec(field: any, probe: any) {
  return (field.income * probe.amountMult) / tripTime(probe)
}
// 投资比 = (矿区造价 + 探机造价 + 探机气耗) ÷ 每秒采集量
function harvestRoi(field: any, probe: any) {
  const ips = harvestPerSec(field, probe)
  if (!ips) return null
  const totalCost = field.cost + (probe.cost || 0) + (probe.gasCost || 0)
  return Math.round(totalCost / ips)
}
// 着色：同一矿区行内，投资比越低越“绿”，越高越“暗”
function roiCellClass(field: any, probe: any, probes: any[]) {
  const vals = probes.map(p => harvestRoi(field, p) as number)
  const min = Math.min(...vals), max = Math.max(...vals)
  const v = harvestRoi(field, probe) as number
  if (max === min) return 'text-survivor-600 dark:text-survivor-400'
  const t = (v - min) / (max - min) // 0=最划算
  if (t < 0.34) return 'text-emerald-600 dark:text-emerald-400 font-semibold'
  if (t < 0.67) return 'text-survivor-600 dark:text-survivor-400'
  return 'text-gray-400 dark:text-gray-500'
}

// —— 坦克挂件经济 ——
// 三档：无挂件(×1,0矿) / 科技实验室(×1.5,+20矿+5气) / 反应堆(×2,+200矿+10气)。
const addonCols = [
  { key: 'none', label: '无挂件', multiplier: 1, cost: 0, gasCost: 0 },
  { key: 'tech', label: '科技实验室 ×1.5', multiplier: 1.5, cost: 20, gasCost: 5 },
  { key: 'reactor', label: '反应堆 ×2', multiplier: 2, cost: 200, gasCost: 10 },
]
function addonPerSec(b: any, col: any) {
  if (!b.income || !b.incomePeriod) return 0
  return (b.income * col.multiplier) / b.incomePeriod
}
function addonRoi(b: any, col: any) {
  const ips = addonPerSec(b, col)
  if (!ips) return null
  return Math.round((b.cost + col.cost) / ips)
}
function addonPayback(b: any, col: any) {
  const ips = addonPerSec(b, col)
  if (!ips) return 0
  return Math.round((b.cost + col.cost) / ips)
}
// 着色：同一建筑行内，投资比越低越“绿”
function addonRoiCellClass(b: any, col: any) {
  const vals = addonCols.map(c => addonRoi(b, c) as number)
  const min = Math.min(...vals), max = Math.max(...vals)
  const v = addonRoi(b, col) as number
  if (max === min) return 'text-survivor-600 dark:text-survivor-400'
  const t = (v - min) / (max - min)
  if (t < 0.34) return 'text-emerald-600 dark:text-emerald-400 font-semibold'
  if (t < 0.67) return 'text-survivor-600 dark:text-survivor-400'
  return 'text-gray-400 dark:text-gray-500'
}

// —— 阿瑞斯装填经济 ——
// 工人装入矿区后周期性产矿；矿区货舱有限，工人按体型占格，
// 故“每格效率”（每秒产矿 ÷ 占格）才是真正的优化指标。三档工人矿物回本均为 100s。
function minerPerSec(m: any) {
  if (!m.income || !m.incomePeriod) return 0
  return m.income / m.incomePeriod
}
function minerPerSpace(m: any) {
  if (!m.cargoSize) return 0
  return minerPerSec(m) / m.cargoSize
}
function minerPayback(m: any) {
  const ips = minerPerSec(m)
  if (!ips || m.cost == null) return 0
  return Math.round(m.cost / ips)
}
// 着色：每格效率越高越“绿”
function minerPerSpaceCellClass(m: any, miners: any[]) {
  const vals = miners.map(x => minerPerSpace(x))
  const min = Math.min(...vals), max = Math.max(...vals)
  const v = minerPerSpace(m)
  if (max === min) return 'text-survivor-600 dark:text-survivor-400'
  const t = (v - min) / (max - min) // 1=最高效
  if (t > 0.66) return 'text-emerald-600 dark:text-emerald-400'
  if (t > 0.33) return 'text-survivor-600 dark:text-survivor-400'
  return 'text-gray-400 dark:text-gray-500'
}
</script>
