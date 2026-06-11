export function useWiki() {
  const { authHeaders } = useAuth()

  async function getPage(slug: string) {
    const { data } = await useFetch(`/api/wiki/${slug}`)
    return data
  }

  async function getPageList() {
    const { data } = await useFetch('/api/wiki')
    return data
  }

  async function savePage(slug: string, payload: { title: string; content: string; category?: string }) {
    return await $fetch(`/api/wiki/${slug}`, {
      method: 'PUT',
      headers: authHeaders.value,
      body: payload,
    })
  }

  async function getHistory(slug: string) {
    const { data } = await useFetch(`/api/wiki/${slug}.history`)
    return data
  }

  return { getPage, getPageList, savePage, getHistory }
}
