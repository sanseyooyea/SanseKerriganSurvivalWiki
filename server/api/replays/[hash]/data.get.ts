import { createReadStream, fstatSync, openSync } from 'fs'
import { createGunzip } from 'zlib'
import { isValidHash, jsonPath } from '~/server/utils/replays'

/**
 * 解析结果 JSON。磁盘上存的就是 gzip，浏览器支持时原样下发（Content-Encoding: gzip，
 * 服务器零压缩开销）；极少数不支持 gzip 的客户端走流式解压。
 * 内容由 hash（原始文件 MD5）唯一确定，但解析器升级后会重新生成，所以只缓存一天。
 */
export default defineEventHandler((event) => {
  const hash = String(getRouterParam(event, 'hash') || '').toLowerCase()
  if (!isValidHash(hash)) throw createError({ statusCode: 400, message: '无效的录像编号' })
  const p = jsonPath(hash)
  // 先打开文件再设响应头：文件若恰好被配额淘汰，返回干净的 404 而不是带着 gzip 头的错误体
  let fd: number
  let size = 0
  try {
    fd = openSync(p, 'r')
    size = fstatSync(fd).size
  } catch {
    throw createError({ statusCode: 404, message: '录像不存在或尚未解析完成' })
  }
  const file = createReadStream(p, { fd, autoClose: true })
  // 客户端中途断开时 pipe 不会销毁源流，手动关掉，防止 fd 泄漏
  event.node.req.on('close', () => { if (!event.node.res.writableFinished) file.destroy() })

  setHeader(event, 'Content-Type', 'application/json; charset=utf-8')
  setHeader(event, 'Cache-Control', 'public, max-age=86400')
  setHeader(event, 'Vary', 'Accept-Encoding')

  if (/\bgzip\b/.test(getHeader(event, 'accept-encoding') || '')) {
    setHeader(event, 'Content-Encoding', 'gzip')
    setHeader(event, 'Content-Length', size)
    return sendStream(event, file)
  }
  const gunzip = createGunzip()
  event.node.req.on('close', () => { if (!event.node.res.writableFinished) gunzip.destroy() })
  return sendStream(event, file.pipe(gunzip))
})
