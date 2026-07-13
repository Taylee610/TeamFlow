// Mirrors the backend's accounts/permissions.py::can_manage_project.
// Not a security boundary (the API enforces the real check) -- this is only
// for deciding which buttons to show.
export function canManageProject(user, project) {
  if (!user || !project) return false
  if (project.owner?.id === user.id) return true
  if (user.role === 'admin') return true
  if (user.role === 'manager') {
    return (project.members || []).some((m) => m.id === user.id)
  }
  return false
}
