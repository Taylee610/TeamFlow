// Mirrors the backend's accounts/permissions.py::can_manage_project.
// Not a security boundary (the API enforces the real check) -- this is only
// for deciding which buttons to show.
export function canManageProject(user, project) {
  if (!user || !project) return false
  return project.can_manage === true
}
