import { signalOperationSuccess } from '../../store/notifications'

/** @deprecated message is ignored — success is shown on the top-bar bell icon. */
export function showToast(_message: string) {
  signalOperationSuccess()
}
