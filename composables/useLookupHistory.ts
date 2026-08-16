// 玩家查询的「最近查询」历史，纯本地：存浏览器 localStorage，不进后端。
// 按句柄去重（重复查同一个只保留最近一次并置顶），带查询时间与结果摘要（MMR）。
export interface LookupHistoryItem {
  handle: string
  at: number                 // 查询时间，epoch ms
  survivor: number | null    // 当时查到的生存者 MMR，外服/无天梯为 null
  kerrigan: number | null    // 当时查到的凯瑞甘 MMR
}

const KEY = 'ks2:lookup-history'
const MAX = 12

export function useLookupHistory() {
  // useState 让本地历史在页面间共享；真正的持久化在 localStorage。
  const items = useState<LookupHistoryItem[]>('lookup-history', () => [])

  function load() {
    if (!import.meta.client) return
    try {
      const raw = localStorage.getItem(KEY)
      const arr = raw ? JSON.parse(raw) : []
      items.value = Array.isArray(arr) ? arr : []
    } catch {
      items.value = []
    }
  }

  function persist() {
    if (!import.meta.client) return
    try {
      localStorage.setItem(KEY, JSON.stringify(items.value))
    } catch {
      // 隐私模式/配额满：静默失败，历史仅当次会话有效
    }
  }

  // 记录一次成功查询。summary 缺省即 null（外服玩家常无 MMR）。
  function record(handle: string, summary: { survivor: number | null; kerrigan: number | null }) {
    const h = handle.trim()
    if (!h) return
    const next = items.value.filter(i => i.handle !== h) // 去重
    next.unshift({ handle: h, at: Date.now(), survivor: summary.survivor, kerrigan: summary.kerrigan })
    items.value = next.slice(0, MAX)
    persist()
  }

  function remove(handle: string) {
    items.value = items.value.filter(i => i.handle !== handle)
    persist()
  }

  function clear() {
    items.value = []
    persist()
  }

  return { items, load, record, remove, clear }
}
