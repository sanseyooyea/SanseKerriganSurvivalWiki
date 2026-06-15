<template>
  <section class="sp-eco">
    <!-- 标题区 -->
    <header class="sp-head">
      <div class="sp-head-glow" aria-hidden="true"></div>
      <div class="flex items-center gap-3">
        <img v-if="data.roleId >= 0" :src="`/icons/${String(data.roleId).padStart(2,'0')}.png`"
          class="w-11 h-11 rounded-lg shadow-sm ring-1 ring-violet-300/40" :alt="data.nameZh" />
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <NuxtLink v-if="data.roleId >= 0" :to="`/classes/${data.roleId}`"
              class="text-lg font-bold text-gray-900 dark:text-gray-100 hover:text-violet-600 dark:hover:text-violet-400 transition-colors">
              {{ data.nameZh }}
            </NuxtLink>
            <span class="sp-badge">金融经济</span>
          </div>
          <div class="text-xs text-gray-400 dark:text-gray-500 font-mono">{{ data.hero }}</div>
        </div>
      </div>
      <p class="sp-summary">{{ data.summary }}</p>
      <p class="sp-luck-note">🔮 {{ data.luckNote }}</p>
    </header>

    <!-- 银行 -->
    <div class="sp-section-label">
      <span>🏦 灵魂银行</span>
      <span class="sp-section-meta">{{ data.bank.cost }} 矿 · 储蓄复利 · 每 {{ data.bank.interestPeriodSec }}s 结算</span>
    </div>
    <div class="sp-card">
      <p class="sp-card-desc">{{ data.bank.desc }}</p>
      <div class="sp-bank-grid">
        <div class="sp-stat"><div class="sp-stat-v">≈1%</div><div class="sp-stat-l">每期利率</div></div>
        <div class="sp-stat"><div class="sp-stat-v">{{ data.bank.interestPeriodSec }}s</div><div class="sp-stat-l">结算周期</div></div>
        <div class="sp-stat"><div class="sp-stat-v">复利</div><div class="sp-stat-l">利息滚存</div></div>
        <div class="sp-stat"><div class="sp-stat-v">10亿</div><div class="sp-stat-l">余额上限</div></div>
      </div>
      <p class="sp-rule-note">{{ data.bank.interestRule }}</p>
      <table class="sp-mini-table">
        <thead><tr><th>余额</th><th>每 {{ data.bank.interestPeriodSec }}s 利息</th></tr></thead>
        <tbody>
          <tr v-for="ex in data.bank.examples" :key="ex.balance">
            <td>{{ ex.balance.toLocaleString() }}</td>
            <td class="sp-gain">+{{ ex.interestPerTick.toLocaleString() }}</td>
          </tr>
        </tbody>
      </table>
      <div class="sp-tiers">存/取档位：{{ data.bank.depositTiers.join(' / ') }}　·　拆除返还全部余额</div>
    </div>

    <!-- 股市 / 证券交易所 -->
    <div class="sp-section-label">
      <span>📈 股市 / 证券交易所</span>
      <span class="sp-section-meta">{{ data.market.marketCost }} / {{ data.market.exchangeCost }} · 周期投资 · 每{{ data.market.tickPeriodSec }}s×{{ data.market.ticksPerCycle }}次 · 锁定 {{ data.market.lockDurationSec }}s</span>
    </div>
    <div class="sp-card">
      <p class="sp-card-desc">{{ data.market.desc }}</p>
      <div class="sp-formula">每周期乘数 = <b>1.0925</b> + 运气 ÷ 5　（60s 内复利 {{ data.market.ticksPerCycle }} 次）</div>
      <div class="sp-power-warn">⚡ {{ data.market.powerRequirement }}</div>
      <table class="sp-mini-table">
        <thead><tr><th>运气</th><th>每周期乘数</th><th>单周期收益(60s)</th></tr></thead>
        <tbody>
          <tr v-for="ex in data.market.multiplierExamples" :key="ex.luck">
            <td>{{ ex.luck > 0 ? '+' + ex.luck : ex.luck }}</td>
            <td class="font-mono">×{{ ex.multiplier }}</td>
            <td :class="ex.multiplier >= 1 ? 'sp-gain' : 'sp-loss'">{{ ex.pctPerCycle }}</td>
          </tr>
        </tbody>
      </table>
      <div class="sp-subhead">💰 投资手续费（气体）</div>
      <p class="sp-tiers">{{ data.market.depositGasNote }}</p>
      <table class="sp-mini-table">
        <thead><tr><th>存入本金</th><th>气体手续费</th><th>费率</th></tr></thead>
        <tbody>
          <tr v-for="d in data.market.depositTiers" :key="String(d.minerals)">
            <td>{{ typeof d.minerals === 'number' ? d.minerals.toLocaleString() + ' 矿' : d.minerals }}</td>
            <td class="sp-loss">{{ d.gas }} 气</td>
            <td>{{ d.rate }}</td>
          </tr>
        </tbody>
      </table>
      <div class="sp-tiers">{{ data.market.withdrawNote }}　{{ data.market.exchangeNote }}</div>
    </div>

    <!-- 赌场 -->
    <div class="sp-section-label">
      <span>🎰 奇迹熔炉（赌场）</span>
      <span class="sp-section-meta">{{ data.casino.cost }} 矿 · 六种博彩 · 运气影响部分玩法</span>
    </div>
    <p class="sp-card-desc px-1 mb-3">{{ data.casino.desc }}</p>
    <div class="sp-casino-grid">
      <div v-for="g in data.casino.games" :key="g.nameZh" class="sp-game-card" :class="{ 'is-luck': g.luckAffected }">
        <div class="sp-game-head">
          <span class="sp-game-name">{{ g.nameZh }}</span>
          <span v-if="g.luckAffected" class="sp-luck-tag">运气</span>
        </div>
        <div class="sp-game-meta">
          <span class="sp-game-stake">赌注：{{ g.stake }}</span>
          <span v-if="g.baseWinChance" class="sp-game-ev">基础胜率 {{ Math.round(g.baseWinChance * 100) }}%</span>
        </div>
        <p class="sp-game-desc">{{ g.desc }}</p>
      </div>
    </div>

    <!-- 水晶球 -->
    <div class="sp-section-label">
      <span>🔮 水晶球</span>
      <span class="sp-section-meta">{{ data.crystalBall.cost }} 矿 · 设定运气值 · 运气贯穿股市与赌博</span>
    </div>
    <div class="sp-card">
      <p class="sp-card-desc">{{ data.crystalBall.desc }}</p>
      <p class="sp-rule-note">{{ data.crystalBall.divinationNote }}</p>

      <!-- 四种占卜：花费越高运气越好 -->
      <div class="sp-divi-grid">
        <div v-for="d in data.crystalBall.divinations" :key="d.id" class="sp-divi-card">
          <div class="sp-divi-head">
            <span class="sp-divi-name">{{ d.nameZh }}</span>
            <span class="sp-divi-cost">{{ d.cost }}</span>
          </div>
          <div class="sp-divi-bar">
            <span class="sp-divi-range">{{ d.luckRange }}</span>
            <span class="sp-divi-mean">均值 {{ d.luckMean > 0 ? '+' : '' }}{{ d.luckMean }}</span>
          </div>
          <p class="sp-divi-desc">{{ d.desc }}</p>
          <div class="sp-divi-neg">负运气概率 {{ Math.round(d.negChance * 100) }}%</div>
        </div>
      </div>

      <div class="sp-luck-scale-label">运气等级对照</div>
      <div class="sp-luck-scale">
        <div v-for="t in data.crystalBall.luckTiers" :key="t.label" class="sp-luck-chip" :class="luckChipClass(t.label)">
          <span class="sp-luck-range">{{ t.range }}</span>
          <span class="sp-luck-label">{{ t.label }}</span>
        </div>
      </div>
      <div class="sp-relic">
        <div class="sp-relic-head">⚠️ {{ data.crystalBall.ancientRelic.nameZh }}</div>
        <p class="sp-relic-desc">{{ data.crystalBall.ancientRelic.desc }}</p>
        <ul class="sp-relic-list">
          <li v-for="(ev, i) in data.crystalBall.ancientRelic.events" :key="i"
            :class="ev.good === true ? 'ev-good' : ev.good === false ? 'ev-bad' : 'ev-neutral'">
            <span class="sp-relic-pct">{{ Math.round(ev.chance * 100) }}%</span>
            <span>{{ ev.effect }}</span>
          </li>
        </ul>
      </div>
    </div>

    <p class="sp-foot-note">{{ data._note }}</p>

    <!-- 经济路径规划器 -->
    <SpiritPlanner />
  </section>
</template>

<script setup lang="ts">
import spiritData from '~/data/spirit-economy.json'
import { useClassData } from '~/composables/useClassData'

const { classes } = useClassData()
const role = classes.find(c => c.nameEn === 'Spirit')
const data = { ...spiritData, roleId: role?.id ?? (spiritData as any).roleId ?? -1 }

function luckChipClass(label: string) {
  if (label.includes('极度幸运')) return 'luck-best'
  if (label.includes('非常幸运')) return 'luck-great'
  if (label.includes('幸运')) return 'luck-good'
  if (label.includes('中立')) return 'luck-mid'
  if (label.includes('极度不幸')) return 'luck-worst'
  if (label.includes('不幸')) return 'luck-bad'
  return 'luck-mid'
}
</script>

<style scoped>
.sp-eco {
  margin-top: 2rem; padding: 1.5rem; border-radius: 1rem;
  border: 1px solid rgb(229, 231, 235);
  background:
    radial-gradient(120% 80% at 0% 0%, rgba(139,92,246,0.07), transparent 60%),
    radial-gradient(120% 80% at 100% 0%, rgba(217,70,239,0.06), transparent 60%);
}
.dark .sp-eco {
  border-color: rgb(55, 65, 81);
  background:
    radial-gradient(120% 80% at 0% 0%, rgba(139,92,246,0.12), transparent 60%),
    radial-gradient(120% 80% at 100% 0%, rgba(217,70,239,0.10), transparent 60%);
}

/* 头部 */
.sp-head { position: relative; margin-bottom: 1.25rem; }
.sp-badge {
  font-size: 0.62rem; font-weight: 700; letter-spacing: 0.08em;
  padding: 0.1rem 0.5rem; border-radius: 999px;
  color: rgb(139,92,246); background: rgba(139,92,246,0.14);
}
.sp-summary { margin-top: 0.75rem; font-size: 0.8rem; line-height: 1.6; color: rgb(107,114,128); }
.dark .sp-summary { color: rgb(156,163,175); }
.sp-luck-note {
  margin-top: 0.6rem; font-size: 0.72rem; line-height: 1.55; padding: 0.55rem 0.7rem;
  border-radius: 0.6rem; color: rgb(124,58,237);
  background: rgba(139,92,246,0.08); border: 1px solid rgba(139,92,246,0.2);
}
.dark .sp-luck-note { color: rgb(196,181,253); background: rgba(139,92,246,0.12); border-color: rgba(139,92,246,0.25); }

/* 区块标题 */
.sp-section-label {
  display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 0.3rem;
  margin: 1.5rem 0 0.7rem; font-size: 0.92rem; font-weight: 700; color: rgb(31,41,55);
}
.dark .sp-section-label { color: rgb(229,231,235); }
.sp-section-meta { font-size: 0.68rem; font-weight: 500; color: rgb(156,163,175); }

/* 卡片 */
.sp-card {
  padding: 1rem; border-radius: 0.8rem;
  background: rgba(255,255,255,0.55); border: 1px solid rgb(229,231,235);
}
.dark .sp-card { background: rgba(31,41,55,0.45); border-color: rgb(55,65,81); }
.sp-card-desc { font-size: 0.76rem; line-height: 1.65; color: rgb(75,85,99); }
.dark .sp-card-desc { color: rgb(156,163,175); }
.sp-rule-note {
  font-size: 0.7rem; line-height: 1.55; color: rgb(107,114,128);
  padding: 0.5rem 0.6rem; margin: 0.5rem 0; border-radius: 0.5rem;
  background: rgba(139,92,246,0.06); border-left: 2px solid rgba(139,92,246,0.4);
}
.dark .sp-rule-note { color: rgb(156,163,175); background: rgba(139,92,246,0.1); }

/* 银行统计格 */
.sp-bank-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 0.5rem; margin: 0.85rem 0; }
.sp-stat { text-align: center; padding: 0.55rem 0.3rem; border-radius: 0.6rem; background: rgba(139,92,246,0.07); }
.dark .sp-stat { background: rgba(139,92,246,0.12); }
.sp-stat-v { font-size: 1rem; font-weight: 800; color: rgb(124,58,237); }
.dark .sp-stat-v { color: rgb(196,181,253); }
.sp-stat-l { font-size: 0.62rem; color: rgb(156,163,175); margin-top: 0.15rem; }

/* 迷你表 */
.sp-mini-table { width: 100%; font-size: 0.74rem; border-collapse: collapse; margin: 0.5rem 0; }
.sp-mini-table th { text-align: left; font-weight: 600; color: rgb(156,163,175); padding: 0.3rem 0.5rem; border-bottom: 1px solid rgb(229,231,235); }
.dark .sp-mini-table th { border-color: rgb(55,65,81); }
.sp-mini-table td { padding: 0.3rem 0.5rem; border-bottom: 1px solid rgba(229,231,235,0.5); color: rgb(55,65,81); }
.dark .sp-mini-table td { border-color: rgba(55,65,81,0.5); color: rgb(209,213,219); }
.sp-gain { color: rgb(16,185,129); font-weight: 600; }
.sp-loss { color: rgb(239,68,68); font-weight: 600; }
.sp-tiers { font-size: 0.68rem; color: rgb(156,163,175); margin-top: 0.5rem; }
.sp-subhead { font-size: 0.75rem; font-weight: 700; color: rgb(124,58,237); margin-top: 0.9rem; }
.dark .sp-subhead { color: rgb(196,181,253); }

/* 公式 / 供能提示 */
.sp-formula {
  font-size: 0.82rem; text-align: center; padding: 0.5rem; margin: 0.6rem 0;
  border-radius: 0.55rem; background: rgba(139,92,246,0.08); color: rgb(124,58,237);
}
.dark .sp-formula { background: rgba(139,92,246,0.14); color: rgb(196,181,253); }
.sp-formula b { font-size: 0.95rem; }
.sp-power-warn {
  font-size: 0.7rem; padding: 0.4rem 0.6rem; border-radius: 0.5rem; margin-bottom: 0.5rem;
  color: rgb(202,138,4); background: rgba(234,179,8,0.1); border: 1px solid rgba(234,179,8,0.25);
}
.dark .sp-power-warn { color: rgb(250,204,21); background: rgba(234,179,8,0.12); }

/* 赌场网格 */
.sp-casino-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px,1fr)); gap: 0.6rem; }
.sp-game-card { padding: 0.75rem; border-radius: 0.7rem; background: rgba(255,255,255,0.55); border: 1px solid rgb(229,231,235); }
.dark .sp-game-card { background: rgba(31,41,55,0.45); border-color: rgb(55,65,81); }
.sp-game-card.is-luck { border-color: rgba(139,92,246,0.35); }
.sp-game-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.3rem; }
.sp-game-name { font-size: 0.84rem; font-weight: 700; color: rgb(31,41,55); }
.dark .sp-game-name { color: rgb(229,231,235); }
.sp-luck-tag { font-size: 0.58rem; font-weight: 700; padding: 0.05rem 0.35rem; border-radius: 999px; color: rgb(139,92,246); background: rgba(139,92,246,0.14); }
.sp-game-meta { display: flex; flex-wrap: wrap; gap: 0.4rem; font-size: 0.64rem; margin-bottom: 0.35rem; }
.sp-game-stake { color: rgb(156,163,175); }
.sp-game-ev { color: rgb(16,185,129); font-weight: 600; }
.sp-game-desc { font-size: 0.7rem; line-height: 1.55; color: rgb(107,114,128); }
.dark .sp-game-desc { color: rgb(156,163,175); }

/* 四种占卜网格 */
.sp-divi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px,1fr)); gap: 0.6rem; margin: 0.85rem 0; }
.sp-divi-card { padding: 0.7rem; border-radius: 0.7rem; background: rgba(139,92,246,0.05); border: 1px solid rgba(139,92,246,0.18); }
.dark .sp-divi-card { background: rgba(139,92,246,0.1); border-color: rgba(139,92,246,0.22); }
.sp-divi-head { display: flex; align-items: baseline; justify-content: space-between; gap: 0.4rem; }
.sp-divi-name { font-size: 0.82rem; font-weight: 700; color: rgb(31,41,55); }
.dark .sp-divi-name { color: rgb(229,231,235); }
.sp-divi-cost { font-size: 0.64rem; font-weight: 600; color: rgb(124,58,237); }
.dark .sp-divi-cost { color: rgb(196,181,253); }
.sp-divi-bar { display: flex; align-items: baseline; justify-content: space-between; gap: 0.4rem; margin: 0.3rem 0; }
.sp-divi-range { font-family: monospace; font-size: 0.66rem; color: rgb(107,114,128); }
.sp-divi-mean { font-size: 0.72rem; font-weight: 700; color: rgb(16,185,129); }
.sp-divi-desc { font-size: 0.68rem; line-height: 1.5; color: rgb(107,114,128); }
.dark .sp-divi-desc { color: rgb(156,163,175); }
.sp-divi-neg { font-size: 0.6rem; color: rgb(239,68,68); margin-top: 0.3rem; }
.sp-luck-scale-label { font-size: 0.7rem; font-weight: 600; color: rgb(107,114,128); margin-top: 0.75rem; }

/* 运气刻度 */
.sp-luck-scale { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.5rem 0 0.85rem; }
.sp-luck-chip { display: flex; flex-direction: column; padding: 0.35rem 0.55rem; border-radius: 0.5rem; font-size: 0.62rem; }
.sp-luck-range { font-family: monospace; opacity: 0.7; }
.sp-luck-label { font-weight: 700; }
.luck-worst { background: rgba(239,68,68,0.15); color: rgb(185,28,28); }
.luck-bad { background: rgba(249,115,22,0.13); color: rgb(194,65,12); }
.luck-mid { background: rgba(156,163,175,0.15); color: rgb(75,85,99); }
.luck-good { background: rgba(59,130,246,0.13); color: rgb(29,78,216); }
.luck-great { background: rgba(16,185,129,0.14); color: rgb(4,120,87); }
.luck-best { background: rgba(139,92,246,0.16); color: rgb(109,40,217); }
.dark .luck-worst { color: rgb(252,165,165); }
.dark .luck-bad { color: rgb(253,186,116); }
.dark .luck-mid { color: rgb(209,213,219); }
.dark .luck-good { color: rgb(147,197,253); }
.dark .luck-great { color: rgb(110,231,183); }
.dark .luck-best { color: rgb(196,181,253); }

/* 古老遗物 */
.sp-relic { margin-top: 0.9rem; padding: 0.75rem; border-radius: 0.7rem; background: rgba(217,70,239,0.06); border: 1px solid rgba(217,70,239,0.2); }
.dark .sp-relic { background: rgba(217,70,239,0.1); border-color: rgba(217,70,239,0.25); }
.sp-relic-head { font-size: 0.8rem; font-weight: 700; color: rgb(162,28,175); }
.dark .sp-relic-head { color: rgb(240,171,252); }
.sp-relic-desc { font-size: 0.7rem; color: rgb(107,114,128); margin: 0.3rem 0 0.5rem; }
.sp-relic-list { display: flex; flex-direction: column; gap: 0.3rem; }
.sp-relic-list li { display: flex; gap: 0.5rem; align-items: baseline; font-size: 0.72rem; }
.sp-relic-pct { font-family: monospace; font-weight: 700; min-width: 2.5rem; }
.ev-good { color: rgb(16,185,129); }
.ev-bad { color: rgb(239,68,68); }
.ev-neutral { color: rgb(107,114,128); }
.dark .ev-good { color: rgb(110,231,183); }
.dark .ev-bad { color: rgb(252,165,165); }
.dark .ev-neutral { color: rgb(156,163,175); }

.sp-foot-note { margin-top: 1.25rem; font-size: 0.65rem; line-height: 1.5; color: rgb(156,163,175); }

@media (max-width: 640px) {
  .sp-bank-grid { grid-template-columns: repeat(2,1fr); }
}
</style>
