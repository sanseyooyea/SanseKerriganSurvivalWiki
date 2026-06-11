import { readFileSync } from 'fs'
import { join } from 'path'

// 读取预翻译的中文映射（scripts/translate_council.py 生成），失败则回退空表
function loadZh(): Record<string, { title?: string; description?: string; close_reason?: string }> {
  try {
    const p = join(process.cwd(), 'data', 'council-zh.json')
    return JSON.parse(readFileSync(p, 'utf-8')).translations || {}
  } catch {
    return {}
  }
}

// 代理 194823.xyz 钻石议会提案投票数据，merge 中文译文后返回，缓存避免频繁回源外站
export default defineCachedEventHandler(async () => {
  try {
    const data = await $fetch<any>('https://194823.xyz/api/proposal_votes_cn.json', {
      headers: { Accept: 'application/json' },
      timeout: 8000,
    })
    const zh = loadZh()
    const proposals = (data.proposals || []).map((p: any) => {
      const t = zh[String(p.proposal_id)]
      if (!t) return p
      // 有中文译文则覆盖，空串回退英文原文
      return {
        ...p,
        title: t.title || p.title,
        description: t.description || p.description,
        close_reason: t.close_reason || p.close_reason,
      }
    })
    return { ...data, proposals }
  } catch (e: any) {
    throw createError({ statusCode: 502, message: '无法获取钻石议会数据' })
  }
}, {
  maxAge: 180, // 提案投票数据周期生成，缓存 3 分钟
  name: 'council',
  getKey: () => 'global',
})
