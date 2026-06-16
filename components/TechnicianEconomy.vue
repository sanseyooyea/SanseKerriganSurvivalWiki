<template>
  <section class="tech-eco">
    <!-- 标题区 -->
    <header class="tech-head">
      <div class="tech-head-glow" aria-hidden="true"></div>
      <div class="flex items-center gap-3">
        <img v-if="data.roleId >= 0" :src="`/icons/${String(data.roleId).padStart(2,'0')}.png`"
          class="w-11 h-11 rounded-lg shadow-sm ring-1 ring-emerald-300/40" :alt="data.nameZh" />
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <NuxtLink v-if="data.roleId >= 0" :to="`/classes/${data.roleId}`"
              class="text-lg font-bold text-gray-900 dark:text-gray-100 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">
              {{ data.nameZh }}
            </NuxtLink>
            <span class="tech-badge">转化经济</span>
          </div>
          <div class="text-xs text-gray-400 dark:text-gray-500 font-mono">{{ data.hero }}</div>
        </div>
      </div>
      <p class="tech-summary">{{ data.summary }}</p>
    </header>

    <!-- 经济闭环图 -->
    <div class="tech-loop">
      <div class="tech-loop-node node-kill">
        <span class="tech-loop-ico">⚔</span>
        <div class="tech-loop-label">塔击杀</div>
        <div class="tech-loop-desc">基础气体 = 造价 ÷ 5</div>
      </div>
      <div class="tech-loop-arrow">
        <span class="tech-loop-mult">×2 / ×3 / ×4</span>
        <svg viewBox="0 0 40 12" fill="none"><path d="M0 6h34m0 0l-5-5m5 5l-5 5" stroke="currentColor" stroke-width="1.5"/></svg>
      </div>
      <div class="tech-loop-node node-gas">
        <span class="tech-loop-ico">⛽</span>
        <div class="tech-loop-label">获得气体</div>
        <div class="tech-loop-desc">倍增器放大</div>
      </div>
      <div class="tech-loop-arrow">
        <span class="tech-loop-mult">转化</span>
        <svg viewBox="0 0 40 12" fill="none"><path d="M0 6h34m0 0l-5-5m5 5l-5 5" stroke="currentColor" stroke-width="1.5"/></svg>
      </div>
      <div class="tech-loop-node node-min">
        <span class="tech-loop-ico">◆</span>
        <div class="tech-loop-label">转化工厂</div>
        <div class="tech-loop-desc">矿+气 → 更多矿</div>
      </div>
    </div>

    <!-- 倍增器 -->
    <div class="tech-section-label">
      <span>倍增器 · 累积光环</span>
      <span class="tech-section-meta">{{ data.killBounty.multiplier.radiusNote }} · 击杀气体与经验同步按倍数结算</span>
    </div>
    <div class="tech-mult-grid">
      <div v-for="m in data.killBounty.multiplier.tiers" :key="m.level" class="tech-mult-card" :class="`mult-${m.multiplier}`">
        <div class="tech-mult-ring">×{{ m.multiplier }}</div>
        <div class="tech-mult-cost">
          <template v-if="m.buildCost">建造 {{ m.buildCost }}</template>
          <template v-else-if="m.upgradeFromX2">升级 {{ m.upgradeFromX2 }}</template>
          <template v-else-if="m.upgradeFromX3">升级 {{ m.upgradeFromX3 }}</template>
          <span class="tech-mult-unit">矿</span>
        </div>
        <div class="tech-mult-range">范围 {{ m.radiusCells }} 格</div>
      </div>
    </div>

    <!-- 转化工厂阶梯表 -->
    <div class="tech-section-label">
      <span>转化工厂 · 八级转化链</span>
      <span class="tech-section-meta">投入 {{ data.transmutation.investSec }}s + 转化 {{ data.transmutation.transmuteSec }}s（周期 {{ data.transmutation.cycleSec }}s）· 可自动施放 / 自动升级</span>
    </div>
    <div class="tech-table-wrap">
      <table class="tech-table">
        <thead>
          <tr>
            <th class="ta-l">工厂</th>
            <th>建造</th>
            <th>升级</th>
            <th class="seg-min">纯矿转化</th>
            <th class="seg-min">回报</th>
            <th class="seg-min" title="纯矿配方每秒净产出 = 单次净赚 ÷ 20s 周期">净产/s</th>
            <th class="seg-min" title="（建造费 + 单次投入矿）÷ 纯矿每秒净产出，多久赚回总成本">回本</th>
            <th class="seg-gas">矿+气转化</th>
            <th class="seg-gas">回报</th>
            <th class="seg-gas">每点气价值</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in data.transmutation.factories" :key="f.tier" class="stagger-item">
            <td class="ta-l tech-tier">+{{ f.tier }}</td>
            <td class="tech-num">{{ f.buildCost }}</td>
            <td class="tech-num tech-dim">{{ f.upgradeCost ?? '—' }}</td>
            <td class="tech-num seg-min">{{ f.mineralRecipe.in }} → {{ f.mineralRecipe.out }}</td>
            <td class="seg-min">
              <span class="tech-pct" :style="pctStyle(f.mineralRecipe.returnPct, 'min')">+{{ f.mineralRecipe.returnPct }}%</span>
            </td>
            <td class="tech-num seg-min">{{ f.mineralRecipe.netPerSec }}<span class="tech-g">矿/s</span></td>
            <td class="tech-num seg-min">{{ f.paybackSec }}<span class="tech-g">s</span></td>
            <td class="tech-num seg-gas">{{ f.gasRecipe.mineralIn }}+{{ f.gasRecipe.gasIn }}<span class="tech-g">g</span> → {{ f.gasRecipe.out }}</td>
            <td class="seg-gas">
              <span class="tech-pct" :style="pctStyle(f.gasRecipe.returnPct, 'gas')">+{{ f.gasRecipe.returnPct }}%</span>
            </td>
            <td class="tech-num seg-gas tech-gasval">{{ f.gasRecipe.gasValue }}<span class="tech-g">矿/气</span></td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="tech-rule">
      <span class="tech-rule-dot dot-min"></span>{{ data.transmutation.mineralReturnRule }}
      <span class="tech-rule-dot dot-gas"></span>{{ data.transmutation.gasReturnRule }}
    </p>

    <!-- 加速关联 -->
    <div class="tech-accel">
      <div class="tech-accel-ico">⚡</div>
      <div class="flex-1 min-w-0">
        <div class="tech-accel-title">
          {{ data.acceleration.ability }} <span class="tech-accel-pct">+{{ data.acceleration.speedupPct }}%</span>
          <span class="tech-accel-spec">持续 {{ data.acceleration.durationSec }}s · {{ data.acceleration.gasCost }} 气 / {{ data.acceleration.energyCost }} 能量 · 冷却 {{ data.acceleration.cooldownSec }}s · 自动施放</span>
        </div>
        <p class="tech-accel-desc">{{ data.acceleration.economyRelation }}</p>
        <div class="tech-accel-levels">
          <div v-for="lv in data.acceleration.levels" :key="lv.level" class="tech-accel-lv">
            <span class="tech-accel-lv-tag">Lv{{ lv.level }}</span>
            <span class="tech-accel-lv-val">半径 {{ lv.radiusCells }} · 最多 {{ lv.maxStructures }} 建筑</span>
          </div>
        </div>
        <p class="tech-accel-note">{{ data.acceleration.effectNote }}</p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import techData from '~/data/technician-economy.json'

const data = techData as any

// 回报率固定色：纯矿青、矿气绿（所有档位回报率统一 +20% / +44%，无梯度）
function pctStyle(_pct: number, kind: 'min' | 'gas') {
  const hue = kind === 'min' ? 190 : 152
  return { color: `hsl(${hue} 70% 48%)`, fontWeight: 700 }
}
</script>

<style scoped>
/* STYLE_PLACEHOLDER */
.tech-eco {
  --gas: #10b981;
  --gas-soft: #34d399;
  --min: #06b6d4;
  --min-soft: #22d3ee;
  position: relative;
  margin-top: 1.5rem;
  padding: 1.5rem;
  border-radius: 1rem;
  background:
    radial-gradient(120% 80% at 0% 0%, rgba(16,185,129,0.06), transparent 60%),
    radial-gradient(120% 80% at 100% 0%, rgba(6,182,212,0.06), transparent 60%);
  border: 1px solid rgb(229, 231, 235);
  box-shadow: 0 8px 28px rgba(0,0,0,0.05);
}
.dark .tech-eco {
  border-color: rgb(55, 65, 81);
  background:
    radial-gradient(120% 80% at 0% 0%, rgba(16,185,129,0.10), transparent 60%),
    radial-gradient(120% 80% at 100% 0%, rgba(6,182,212,0.10), transparent 60%);
}

/* 头部 */
.tech-head { position: relative; margin-bottom: 1.25rem; }
.tech-badge {
  font-size: 0.62rem; font-weight: 700; letter-spacing: 0.08em;
  padding: 0.1rem 0.5rem; border-radius: 999px;
  color: var(--gas); background: color-mix(in srgb, var(--gas) 14%, transparent);
}
.tech-summary {
  margin-top: 0.75rem; font-size: 0.8rem; line-height: 1.6;
  color: rgb(107, 114, 128);
}
.dark .tech-summary { color: rgb(156, 163, 175); }

/* 经济闭环图 */
.tech-loop {
  display: flex; align-items: stretch; gap: 0.4rem;
  margin: 1.25rem 0 1.75rem; flex-wrap: wrap;
}
.tech-loop-node {
  flex: 1 1 0; min-width: 90px;
  display: flex; flex-direction: column; align-items: center; text-align: center;
  padding: 0.85rem 0.5rem; border-radius: 0.75rem;
  background: rgba(255,255,255,0.6); border: 1px solid rgb(229,231,235);
}
.dark .tech-loop-node { background: rgba(31,41,55,0.5); border-color: rgb(55,65,81); }
.node-gas { border-color: color-mix(in srgb, var(--gas) 40%, transparent); }
.node-min { border-color: color-mix(in srgb, var(--min) 40%, transparent); }
.tech-loop-ico { font-size: 1.35rem; line-height: 1; margin-bottom: 0.4rem; }
.node-gas .tech-loop-ico { color: var(--gas); }
.node-min .tech-loop-ico { color: var(--min); }
.tech-loop-label { font-size: 0.8rem; font-weight: 600; color: rgb(31,41,55); }
.dark .tech-loop-label { color: rgb(229,231,235); }
.tech-loop-desc { font-size: 0.65rem; color: rgb(156,163,175); margin-top: 0.15rem; }
.tech-loop-arrow {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 0.2rem; color: rgb(203,213,225); padding: 0 0.1rem;
}
.dark .tech-loop-arrow { color: rgb(75,85,99); }
.tech-loop-arrow svg { width: 34px; height: 12px; }
.tech-loop-mult {
  font-family: 'JetBrains Mono', monospace; font-size: 0.58rem; font-weight: 700;
  color: var(--gas); white-space: nowrap;
}

/* 区段标签 */
.tech-section-label {
  display: flex; align-items: baseline; gap: 0.6rem; flex-wrap: wrap;
  margin: 1.5rem 0 0.75rem;
  font-size: 0.8rem; font-weight: 700; color: rgb(55,65,81);
}
.dark .tech-section-label { color: rgb(209,213,219); }
.tech-section-meta { font-size: 0.66rem; font-weight: 400; color: rgb(156,163,175); }

/* 倍增器 */
.tech-mult-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.6rem; }
.tech-mult-card {
  display: flex; flex-direction: column; align-items: center; gap: 0.5rem;
  padding: 1rem 0.5rem; border-radius: 0.85rem;
  background: rgba(255,255,255,0.6); border: 1px solid rgb(229,231,235);
  transition: transform 0.2s, box-shadow 0.2s;
}
.dark .tech-mult-card { background: rgba(31,41,55,0.5); border-color: rgb(55,65,81); }
.tech-mult-card:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(16,185,129,0.15); }
.tech-mult-ring {
  width: 3rem; height: 3rem; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 1.1rem;
  color: #fff; position: relative;
}
.mult-2 .tech-mult-ring { background: linear-gradient(135deg, #34d399, #10b981); box-shadow: 0 0 0 4px rgba(16,185,129,0.15); }
.mult-3 .tech-mult-ring { background: linear-gradient(135deg, #2dd4bf, #0d9488); box-shadow: 0 0 0 4px rgba(13,148,136,0.18); }
.mult-4 .tech-mult-ring { background: linear-gradient(135deg, #22d3ee, #0891b2); box-shadow: 0 0 0 4px rgba(8,145,178,0.2); }
.tech-mult-cost {
  font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; font-weight: 600;
  color: rgb(75,85,99);
}
.dark .tech-mult-cost { color: rgb(203,213,225); }
.tech-mult-unit { font-size: 0.6rem; color: rgb(156,163,175); margin-left: 0.15rem; }
.tech-mult-range {
  font-family: 'JetBrains Mono', monospace; font-size: 0.62rem;
  color: rgb(156,163,175); margin-top: 0.15rem;
}
.dark .tech-mult-range { color: rgb(148,163,184); }

/* 转化工厂阶梯表 */
.tech-table-wrap { overflow-x: auto; margin: 0 -0.25rem; }
.tech-table { width: 100%; min-width: 600px; border-collapse: collapse; font-size: 0.8rem; }
.tech-table thead th {
  font-size: 0.62rem; font-weight: 600; letter-spacing: 0.04em;
  text-transform: uppercase; color: rgb(156,163,175);
  padding: 0.4rem 0.6rem; text-align: right; white-space: nowrap;
  border-bottom: 1px solid rgb(229,231,235);
}
.dark .tech-table thead th { border-color: rgb(55,65,81); }
.tech-table th.ta-l, .tech-table td.ta-l { text-align: left; }
.tech-table th.seg-min { color: var(--min); }
.tech-table th.seg-gas { color: var(--gas); }
.tech-table tbody td {
  padding: 0.5rem 0.6rem; text-align: right;
  border-bottom: 1px solid rgb(243,244,246);
}
.dark .tech-table tbody td { border-color: rgba(55,65,81,0.5); }
.tech-table tbody tr:last-child td { border-bottom: none; }
.tech-table tbody tr { transition: background 0.15s; }
.tech-table tbody tr:hover { background: rgba(16,185,129,0.04); }
.tech-num { font-family: 'JetBrains Mono', monospace; color: rgb(55,65,81); }
.dark .tech-num { color: rgb(203,213,225); }
.tech-dim { color: rgb(156,163,175); }
.tech-tier {
  font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 0.9rem;
  color: rgb(17,24,39);
}
.dark .tech-tier { color: rgb(243,244,246); }
.seg-min { background: rgba(6,182,212,0.04); }
.seg-gas { background: rgba(16,185,129,0.04); }
.dark .seg-min { background: rgba(6,182,212,0.07); }
.dark .seg-gas { background: rgba(16,185,129,0.07); }
.tech-g { font-size: 0.6rem; color: rgb(156,163,175); margin-left: 0.1rem; }
.tech-gasval { font-weight: 600; }
.tech-pct { font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; }

/* 回报率规则 */
.tech-rule {
  margin-top: 0.75rem; font-size: 0.7rem; line-height: 1.7;
  color: rgb(107,114,128); display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem;
}
.dark .tech-rule { color: rgb(156,163,175); }
.tech-rule-dot { width: 7px; height: 7px; border-radius: 2px; transform: rotate(45deg); display: inline-block; }
.tech-rule-dot.dot-min { background: var(--min); margin-left: 0.5rem; }
.tech-rule-dot.dot-gas { background: var(--gas); margin-left: 0.5rem; }

/* 加速关联 */
.tech-accel {
  display: flex; gap: 0.85rem; align-items: flex-start;
  margin-top: 1.5rem; padding: 1rem 1.1rem; border-radius: 0.85rem;
  background: linear-gradient(100deg, rgba(250,204,21,0.08), transparent 70%);
  border: 1px solid rgba(250,204,21,0.25);
}
.tech-accel-ico {
  font-size: 1.4rem; line-height: 1; flex-shrink: 0;
  filter: drop-shadow(0 0 6px rgba(250,204,21,0.5));
}
.tech-accel-title {
  font-size: 0.85rem; font-weight: 700; color: rgb(146,64,14);
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.5rem;
}
.dark .tech-accel-title { color: rgb(253,224,71); }
.tech-accel-spec { font-size: 0.64rem; font-weight: 400; color: rgb(161,98,7); }
.dark .tech-accel-spec { color: rgb(202,138,4); }
.tech-accel-desc {
  margin-top: 0.3rem; font-size: 0.74rem; line-height: 1.55;
  color: rgb(120,113,108);
}
.dark .tech-accel-desc { color: rgb(168,162,158); }
.tech-accel-pct {
  font-size: 0.8rem; font-weight: 800; color: rgb(202,138,4);
}
.dark .tech-accel-pct { color: rgb(250,204,21); }
.tech-accel-levels {
  display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem;
}
.tech-accel-lv {
  display: inline-flex; align-items: baseline; gap: 0.3rem;
  padding: 0.2rem 0.5rem; border-radius: 0.4rem;
  background: rgba(250,204,21,0.1); border: 1px solid rgba(250,204,21,0.2);
  font-size: 0.66rem;
}
.tech-accel-lv-tag {
  font-family: 'JetBrains Mono', monospace; font-weight: 700; color: rgb(146,64,14);
}
.dark .tech-accel-lv-tag { color: rgb(253,224,71); }
.tech-accel-lv-val { color: rgb(120,113,108); }
.dark .tech-accel-lv-val { color: rgb(168,162,158); }
.tech-accel-note {
  margin-top: 0.4rem; font-size: 0.66rem; color: rgb(161,98,7); font-style: italic;
}
.dark .tech-accel-note { color: rgb(202,138,4); }

@media (max-width: 480px) {
  .tech-loop-desc { display: none; }
  .tech-mult-ring { width: 2.5rem; height: 2.5rem; font-size: 0.95rem; }
}
@media (prefers-reduced-motion: reduce) {
  .tech-mult-card, .tech-table tbody tr { transition: none; }
}
</style>
