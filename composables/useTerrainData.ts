import terrain from '~/data/terrain.json'

/**
 * 地形数据集中层：供 /terrain 大图页与石头模拟器复用。
 * 数据由 scripts/build_terrain.py 从地图 MPQ 提取（Regions/Minimap.tga/t3CellFlags）。
 *
 * 坐标系：世界 256×256 cell，左下为原点(y 向上)；Minimap.png 1024×1024、左上为原点。
 *   px = worldX * pxPerCell
 *   py = (worldSize − worldY) * pxPerCell     // Y 翻转，贴合图片左上原点
 * 通行网格 pathing.bits：行主序位域，索引 i = cy*w + cx（cy=0 为世界 y=0，即底部）。
 */

export interface RockCandidate {
  n: number      // Ramp 区域编号
  x: number      // 世界坐标（quad 中点，0..256）
  y: number
  model?: string // 仅位置相关模型（如 FourSeasons）才逐点带
}

export interface TerrainData {
  map: string
  mapKey: string
  tileset: string
  worldSize: number
  minimap: { path: string; pxPerCell: number; originY: string }
  playableBounds: [number, number, number, number]
  rockModel: string | null
  rockProbDefault: number
  rockCandidates: RockCandidate[]
  pathing: { w: number; h: number; bits: string; cliff: string; cliffStep: number }
}

const T = terrain as unknown as TerrainData

// base64 → 位域字节（构建期常量，解一次即可）
function decodeBits(b64: string): Uint8Array {
  const bin = typeof atob === 'function'
    ? atob(b64)
    : Buffer.from(b64, 'base64').toString('binary')
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out
}

// base64 → 逐 cell 悬崖高度字节（行主序，1 字节/cell）
function decodeBytes(b64: string): Uint8Array {
  const bin = typeof atob === 'function'
    ? atob(b64)
    : Buffer.from(b64, 'base64').toString('binary')
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out
}

let _bits: Uint8Array | null = null
function bits(): Uint8Array {
  if (!_bits) _bits = decodeBits(T.pathing.bits)
  return _bits
}

let _cliff: Uint8Array | null = null
function cliff(): Uint8Array {
  if (!_cliff) _cliff = decodeBytes(T.pathing.cliff)
  return _cliff
}

export function useTerrainData() {
  const px = T.minimap.pxPerCell
  const size = T.worldSize

  /** 世界坐标 → minimap 像素（左上原点） */
  function worldToPx(x: number, y: number): { px: number; py: number } {
    return { px: x * px, py: (size - y) * px }
  }

  /** minimap 像素 → 世界坐标（供 hover 反查） */
  function pxToWorld(pxX: number, pxY: number): { x: number; y: number } {
    return { x: pxX / px, y: size - pxY / px }
  }

  /** 该 cell 是否可通行（bit 0x02；越界视为不可通行） */
  function isPassable(cx: number, cy: number): boolean {
    const w = T.pathing.w
    const h = T.pathing.h
    if (cx < 0 || cy < 0 || cx >= w || cy >= h) return false
    const i = cy * w + cx
    return (bits()[i >> 3] & (1 << (i & 7))) !== 0
  }

  /** 世界坐标点是否可通行（取所在 cell） */
  function isPointPassable(x: number, y: number): boolean {
    return isPassable(Math.floor(x), Math.floor(y))
  }

  /** 该 cell 的悬崖高度层级（0..192；越界返回 0） */
  function cliffAt(cx: number, cy: number): number {
    const w = T.pathing.w
    const h = T.pathing.h
    if (cx < 0 || cy < 0 || cx >= w || cy >= h) return 0
    return cliff()[cy * w + cx]
  }

  return {
    terrain: T,
    imgSize: size * px, // minimap 边长（像素）
    worldToPx,
    pxToWorld,
    isPassable,
    isPointPassable,
    cliffAt,
    cliffStep: T.pathing.cliffStep, // 相邻高差 > 此值即悬崖（不可跨越，只有斜坡能连通台地）
  }
}
