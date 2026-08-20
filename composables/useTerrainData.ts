import indexData from '~/data/terrain.json'

/**
 * 地形数据集中层：供 /terrain 大图页与石头模拟器复用。
 *
 * 多地图结构：
 *   data/terrain.json          轻量索引（构建期 import），列出所有已提取地形
 *   public/terrain/<key>.json  单图完整数据（按需 fetch，含候选点 + 通行/悬崖网格）
 *   public/maps/<key>.png      单图小地图底图
 * 数据由 scripts/build_terrain.py / harvest_terrains.py 从地图 MPQ 提取。
 *
 * 坐标系：世界 worldSize×worldSize cell，左下为原点(y 向上)；minimap 左上为原点。
 *   px = worldX * pxPerCell
 *   py = (worldSize − worldY) * pxPerCell     // Y 翻转，贴合图片左上原点
 * 通行网格 pathing.bits：行主序位域，索引 i = cy*w + cx（cy=0 为世界 y=0，即底部）。
 * 悬崖网格 pathing.cliff：行主序 uint16 LE，逐 cell 高度层（可达 576，故非单字节）。
 */

export interface RockCandidate {
  n: number      // Ramp 区域编号
  x: number      // 世界坐标（quad 中点）
  y: number
  model?: string // 仅位置相关模型（如 FourSeasons）才逐点带
}

export interface FullTerrain {
  key: string
  map: string
  nameZh: string
  tileset: string
  worldSize: number
  minimap: { path: string; pxPerCell: number; originY: string }
  playableBounds: [number, number, number, number]
  rockModel: string | null
  rockProbDefault: number
  rockCandidates: RockCandidate[]
  pathing: { w: number; h: number; bits: string; cliff: string; cliffStep: number; block?: string }
  date?: string
}

export interface MapIndexEntry {
  key: string
  map: string
  nameZh: string
  tileset: string
  worldSize: number
  minimap: string
  rockModel: string | null
  rockProbDefault: number
  candidateCount: number
  date: string | null
}

export interface TerrainIndex {
  defaultMap: string
  maps: MapIndexEntry[]
}

/** 一张已解码地形：自带坐标变换与网格查询，供组件直接消费 */
export interface TerrainView {
  data: FullTerrain
  imgSize: number
  worldToPx: (x: number, y: number) => { px: number; py: number }
  pxToWorld: (pxX: number, pxY: number) => { x: number; y: number }
  isPassable: (cx: number, cy: number) => boolean
  isPointPassable: (x: number, y: number) => boolean
  isBlocked: (cx: number, cy: number) => boolean
  cliffAt: (cx: number, cy: number) => number
  cliffStep: number
}

const INDEX = indexData as unknown as TerrainIndex

// base64 → 位域字节（每 cell 1 bit）
function decodeBits(b64: string): Uint8Array {
  const bin = typeof atob === 'function'
    ? atob(b64)
    : Buffer.from(b64, 'base64').toString('binary')
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out
}

// base64 → 逐 cell 悬崖高度层（uint16 LE，1 值/cell）
function decodeU16(b64: string): Uint16Array {
  const bytes = decodeBits(b64) // 复用 base64→字节
  // 浏览器/Node 均为小端；直接按 buffer 视图解成 uint16
  return new Uint16Array(bytes.buffer, bytes.byteOffset, bytes.byteLength >> 1)
}

/** 由单图完整数据构造视图（解码一次网格，闭包缓存） */
function makeView(full: FullTerrain): TerrainView {
  const px = full.minimap.pxPerCell
  const size = full.worldSize
  const w = full.pathing.w
  const h = full.pathing.h
  const bits = decodeBits(full.pathing.bits)
  const cliff = decodeU16(full.pathing.cliff)
  // 永久阻挡位域（doodad/瞭望塔）：老 json 无此字段时留空 → isBlocked 恒 false（向后兼容）
  const block = full.pathing.block ? decodeBits(full.pathing.block) : null

  const worldToPx = (x: number, y: number) => ({ px: x * px, py: (size - y) * px })
  const pxToWorld = (pxX: number, pxY: number) => ({ x: pxX / px, y: size - pxY / px })

  const isPassable = (cx: number, cy: number): boolean => {
    if (cx < 0 || cy < 0 || cx >= w || cy >= h) return false
    const i = cy * w + cx
    return (bits[i >> 3] & (1 << (i & 7))) !== 0
  }
  const isPointPassable = (x: number, y: number) => isPassable(Math.floor(x), Math.floor(y))

  // 永久阻挡（doodad/瞭望塔）：无 block 层时恒 false
  const isBlocked = (cx: number, cy: number): boolean => {
    if (!block || cx < 0 || cy < 0 || cx >= w || cy >= h) return false
    const i = cy * w + cx
    return (block[i >> 3] & (1 << (i & 7))) !== 0
  }

  const cliffAt = (cx: number, cy: number): number => {
    if (cx < 0 || cy < 0 || cx >= w || cy >= h) return 0
    return cliff[cy * w + cx]
  }

  return {
    data: full,
    imgSize: size * px,
    worldToPx,
    pxToWorld,
    isPassable,
    isPointPassable,
    isBlocked,
    cliffAt,
    cliffStep: full.pathing.cliffStep,
  }
}

const _cache = new Map<string, TerrainView>()

export function useTerrainData() {
  /** 按需加载并解码一张地形（结果缓存，重复选择不再 fetch） */
  async function loadMap(key: string): Promise<TerrainView> {
    const cached = _cache.get(key)
    if (cached) return cached
    const full = await $fetch<FullTerrain>(`/terrain/${key}.json`)
    const view = makeView(full)
    _cache.set(key, view)
    return view
  }

  return {
    index: INDEX,
    defaultMap: INDEX.defaultMap,
    maps: INDEX.maps,
    loadMap,
  }
}
