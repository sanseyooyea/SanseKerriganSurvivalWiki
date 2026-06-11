import { requireUser } from '~/server/utils/auth'

export default defineEventHandler(async (event) => {
  const user = requireUser(event)
  return { user: { id: user.id, username: user.username, role: user.role, handle: user.handle || '' } }
})
