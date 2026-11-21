import type { ChangeRequestStatus } from "../api/types";
import { Badge } from "../components/ui/Badge";

export const CHANGE_REQUEST_STATUS_BADGE: Record<
  ChangeRequestStatus,
  {
    label: string;
    variant: "info" | "success" | "error" | "warning" | "default";
  }
> = {
  open: { label: "Open", variant: "info" },
  applied: { label: "Applied", variant: "success" },
  rejected: { label: "Rejected", variant: "error" },
  withdrawn: { label: "Withdrawn", variant: "warning" },
};

export function ChangeRequestStatusBadge({
  status,
}: {
  status: ChangeRequestStatus;
}) {
  const { label, variant } = CHANGE_REQUEST_STATUS_BADGE[status];
  return <Badge variant={variant}>{label}</Badge>;
}
