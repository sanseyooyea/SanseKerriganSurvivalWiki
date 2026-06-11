export interface User {
  id: number
  username: string
  role: 'admin' | 'editor' | 'user'
  handle?: string
}

export function useAuth() {
  const user = useState<User | null>('auth-user', () => null)
  const token = useState<string | null>('auth-token', () => null)

  const isLoggedIn = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const canEdit = computed(() => user.value?.role === 'admin' || user.value?.role === 'editor')

  const setAuth = (t: string, u: User) => {
    token.value = t
    user.value = u
    if (import.meta.client) {
      localStorage.setItem('auth-token', t)
    }
  }

  const logout = () => {
    token.value = null
    user.value = null
    if (import.meta.client) {
      localStorage.removeItem('auth-token')
    }
  }

  const init = async () => {
    if (!import.meta.client) return
    const saved = localStorage.getItem('auth-token')
    if (!saved) return
    token.value = saved
    try {
      const res = await $fetch<{ user: User }>('/api/auth/me', {
        headers: { Authorization: `Bearer ${saved}` }
      })
      user.value = res.user
    } catch {
      logout()
    }
  }

  const authHeaders = computed(() =>
    token.value ? { Authorization: `Bearer ${token.value}` } : {}
  )

  return { user, token, isLoggedIn, isAdmin, canEdit, setAuth, logout, init, authHeaders }
}
