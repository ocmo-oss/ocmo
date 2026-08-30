import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { treeApi } from "../../api/tree";
import type { FolderNode } from "../../api/types";
import type { useItemPermissions } from "../../hooks/useItemPermissions";
import { ItemHeader } from "./ItemHeader";
import { ItemDescription } from "./ItemDescription";
import { ItemAuditTab } from "./ItemAuditTab";
import { ResolvePanel } from "../resolve/ResolvePanel";
import { ItemIcon } from "../../lib/itemTypes";
import { SkeletonList } from "../ui/Skeleton";
import { DeleteDialog } from "./DeleteDialog";
import { LocationDialog } from "./LocationDialog";
import { PermissionDenied } from "./PermissionDenied";
import { cn } from "../ui/cn";

type Tab = "contents" | "resolve" | "audit";

export default function FolderView({
  item,
  namespace,
  permissions,
}: {
  item: FolderNode;
  namespace: string;
  permissions: ReturnType<typeof useItemPermissions>;
}) {
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [moveOpen, setMoveOpen] = useState(false);
  const [copyOpen, setCopyOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("contents");

  useEffect(() => {
    setActiveTab("contents");
  }, [item.path]);

  const { data, isLoading } = useQuery({
    queryKey: ["tree-nav", namespace, item.path],
    queryFn: ({ signal }) =>
      treeApi.navigate(namespace, item.path, { limit: 100 }, signal),
    staleTime: 30_000,
    enabled: permissions.canRead,
  });

  return (
    <div className="flex h-full flex-col">
      <ItemHeader
        namespace={namespace}
        path={item.path}
        type="folder"
        onDelete={permissions.canDelete ? () => setDeleteOpen(true) : undefined}
        onMove={permissions.canMove ? () => setMoveOpen(true) : undefined}
        onCopy={permissions.canCopy ? () => setCopyOpen(true) : undefined}
      />
      <ItemDescription
        namespace={namespace}
        path={item.path}
        description={item.description}
        canEdit={permissions.canDescribe}
      />
      <div className="flex items-center gap-0.5 border-b px-4 dark:border-gray-700">
        {[
          { id: "contents" as const, label: "Contents" },
          ...(permissions.canResolve
            ? [{ id: "resolve" as const, label: "Resolve" }]
            : []),
          ...(permissions.canAudit
            ? [{ id: "audit" as const, label: "Audit" }]
            : []),
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "border-b-2 px-3 py-2 text-xs font-medium transition-colors",
              activeTab === tab.id
                ? "border-brand-500 text-brand-700 dark:text-brand-300"
                : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {activeTab === "contents" && (
        <div className="flex-1 overflow-auto p-6">
          {!permissions.canRead ? (
            <PermissionDenied message="You do not have permission to view this folder contents." />
          ) : (
            <>
              <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">
                Contents
              </h2>
              {isLoading && <SkeletonList count={4} />}
              {!isLoading && data?.children.length === 0 && (
                <p className="text-sm text-gray-400">This folder is empty</p>
              )}
              <div className="grid gap-2">
                {data?.children.map((child) => (
                  <Link
                    key={child.path}
                    to={`/ns/${namespace}/configs/${child.path}`}
                    className="flex items-center gap-3 rounded-lg border px-4 py-3 hover:bg-slate-100 dark:border-gray-700 dark:hover:bg-gray-800"
                  >
                    <ItemIcon type={child.type} />
                    <span className="font-mono text-sm text-gray-800 dark:text-gray-200">
                      {child.name}
                    </span>
                  </Link>
                ))}
              </div>
            </>
          )}
        </div>
      )}
      {activeTab === "resolve" && (
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          {permissions.canResolve ? (
            <ResolvePanel
              namespace={namespace}
              path={item.path}
              mode="folder"
              embedded
            />
          ) : (
            <PermissionDenied message="You do not have permission to resolve configs in this folder." />
          )}
        </div>
      )}
      {activeTab === "audit" && (
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <ItemAuditTab namespace={namespace} path={item.path} type="folder" />
        </div>
      )}
      <DeleteDialog
        namespace={namespace}
        path={item.path}
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
      />
      <LocationDialog
        mode="move"
        namespace={namespace}
        path={item.path}
        type="folder"
        open={moveOpen}
        onClose={() => setMoveOpen(false)}
      />
      <LocationDialog
        mode="copy"
        namespace={namespace}
        path={item.path}
        type="folder"
        open={copyOpen}
        onClose={() => setCopyOpen(false)}
      />
    </div>
  );
}
