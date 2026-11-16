type Mode = 'light' | 'dark'

const STORAGE_KEY = 'color-mode'

function systemMode(): Mode {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

// 同步 .dark（Tailwind dark: 变体）与 CSS color-scheme（让滚动条、表单控件等原生 UI 跟着变色）
function apply(mode: Mode) {
  const root = document.documentElement
  root.classList.toggle('dark', mode === 'dark')
  root.style.colorScheme = mode
}

export function useColorMode() {
  const mode = useState<Mode>('color-mode', () => 'light')

  // 两态切换：目标 = 当前看到的反面。
  // 与系统偏好不同才存 localStorage；与系统一致说明用户在「撤销覆盖」，删除存储值，
  // 以后重新跟随系统。只在写入时判断，不会因系统后来变得一致就自动清除。
  const toggle = () => {
    mode.value = mode.value === 'light' ? 'dark' : 'light'
    if (import.meta.client) {
      apply(mode.value)
      try {
        if (mode.value === systemMode()) localStorage.removeItem(STORAGE_KEY)
        else localStorage.setItem(STORAGE_KEY, mode.value)
      } catch {}
    }
  }

  const init = () => {
    if (!import.meta.client) return
    let saved: Mode | null = null
    try { saved = localStorage.getItem(STORAGE_KEY) as Mode | null } catch {}
    mode.value = saved === 'light' || saved === 'dark' ? saved : systemMode()
    apply(mode.value)

    // 没有手动覆盖时，跟随系统深浅色的实时切换
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      let stored: string | null = null
      try { stored = localStorage.getItem(STORAGE_KEY) } catch {}
      if (stored) return
      mode.value = e.matches ? 'dark' : 'light'
      apply(mode.value)
    })
  }

  return { mode, toggle, init }
}
