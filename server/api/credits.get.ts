const CHARSET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'

function decodeCode(numStr: string): string {
  let t = BigInt(numStr)
  if (t === 0n) return CHARSET[0]
  const n: string[] = []
  while (t > 0n) {
    n.push(CHARSET[Number(t % 64n)])
    t = t / 64n
  }
  return n.reverse().join('')
}

export default defineCachedEventHandler(async (event) => {
  const handle = getQuery(event).handle as string
  if (!handle) {
    throw createError({ statusCode: 400, message: '缺少handle参数' })
  }

  try {
    const data = await $fetch<any>(`https://194823.xyz/api/credits?player_handle=${encodeURIComponent(handle)}`, {
      headers: { Accept: 'application/json' },
      timeout: 8000,
    })
    if (!data) return null

    let totalCredits = 0
    let lucyCredits = 0
    if (data.code) {
      const numPart = data.code.split('/')[0]
      try {
        const decoded = decodeCode(numPart)
        const parts = decoded.split('_')
        totalCredits = parseInt(parts[1] || '0', 10)
        lucyCredits = parseInt(parts[2] || '0', 10)
      } catch {}
    }

    const baseCredits = (data.replays || 0) * 2 - (data.penalty || 0) * 10
    const bonusCredits = lucyCredits - baseCredits

    return {
      replays: data.replays || 0,
      penalty: data.penalty || 0,
      code: data.code || '',
      totalCredits,
      baseCredits,
      bonusCredits,
    }
  } catch (e: any) {
    if (e.status === 404 || e.statusCode === 404) {
      return null
    }
    throw createError({ statusCode: 502, message: '无法获取积分数据' })
  }
}, {
  maxAge: 30,
  name: 'credits',
  getKey: (event) => (getQuery(event).handle as string) || 'none',
})
