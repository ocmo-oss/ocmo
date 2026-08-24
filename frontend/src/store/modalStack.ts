/** Tracks open modal IDs so notifications can route inline instead of opening the tray. */

const stack: string[] = []

export function registerModal(id: string) {
  stack.push(id)
}

export function unregisterModal(id: string) {
  const idx = stack.indexOf(id)
  if (idx !== -1) stack.splice(idx, 1)
}

export function getTopModalId(): string | undefined {
  return stack.at(-1)
}

export function isModalOpen(): boolean {
  return stack.length > 0
}
