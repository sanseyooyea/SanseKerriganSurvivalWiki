// 复制文本到剪贴板，兼容非安全上下文（HTTP / IP 访问）。
// navigator.clipboard 仅在安全上下文（HTTPS 或 localhost）下可用，
// 用户若访问 http://<ip>:8080 时它为 undefined，writeText 会抛错。
// 这里回退到已废弃但广泛支持的 document.execCommand('copy')。
export async function copyText(text: string): Promise<boolean> {
  // 优先用现代 API（安全上下文）
  if (typeof navigator !== 'undefined' && navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // 落到 execCommand 回退
    }
  }

  // 回退：隐藏 textarea + execCommand('copy')，非安全上下文也能用
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    ta.style.position = 'fixed'
    ta.style.top = '0'
    ta.style.left = '0'
    ta.style.opacity = '0'
    ta.style.pointerEvents = 'none'
    document.body.appendChild(ta)
    ta.focus()
    ta.select()
    ta.setSelectionRange(0, text.length)
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  } catch {
    return false
  }
}
