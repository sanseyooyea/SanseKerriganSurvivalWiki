export function useColorMode() {
  const mode = useState<'light' | 'dark'>('color-mode', () => 'light')

  const toggle = () => {
    mode.value = mode.value === 'light' ? 'dark' : 'light'
    if (import.meta.client) {
      document.documentElement.classList.toggle('dark', mode.value === 'dark')
      localStorage.setItem('color-mode', mode.value)
    }
  }

  const init = () => {
    if (!import.meta.client) return
    const saved = localStorage.getItem('color-mode') as 'light' | 'dark' | null
    const preferred = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    mode.value = saved || preferred
    document.documentElement.classList.toggle('dark', mode.value === 'dark')
  }

  return { mode, toggle, init }
}
