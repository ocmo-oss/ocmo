import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { treeApi } from "../../api/tree";
import type { ItemType, TagInfo } from "../../api/types";
import { PathSearchCombobox } from "../diff/PathSearchCombobox";
import { normalizeTreePath } from "../../lib/builtinPaths";
import {
  buildDestinationPathFromFolder,
  validateRelocationTargetPath,
  filterTreePathInput,
} from "../../lib/locationPath";
import { ITEM_TYPE_LABELS } from "../../lib/itemTypes";
import { pathSegments } from "../../lib/paths";
import { refreshTreeQueries } from "../../lib/treeQuery";
import { Modal } from "../ui/Modal";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { useConfigMetadataKey } from "../../store/health";
import { pushApiError } from "../../store/notifications";
import { showToast } from "../ui/Toast";

const VERSIONED_TYPES = new Set<ItemType>(["config", "template", "secret"]);
const MOVE_WARNING_TYPES = new Set<ItemType>(["config", "folder"]);
const REFERENCE_VALIDATION_TYPES = new Set<ItemType>(["config", "folder"]);

function showsCopyTagField(type: ItemType, isMove: boolean): boolean {
  return !isMove && (VERSIONED_TYPES.has(type) || type === "folder");
}

interface LocationDialogProps {
  mode: "move" | "copy";
  namespace: string;
  path: string;
  type: ItemType;
  tags?: TagInfo[];
  open: boolean;
  onClose: () => void;
}

export function LocationDialog({
  mode,
  namespace,
  path,
  type,
  tags = [],
  open,
  onClose,
}: LocationDialogProps) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const configMetadataKey = useConfigMetadataKey();
  const [targetPath, setTargetPath] = useState("");
  const [tagToCopy, setTagToCopy] = useState("latest");
  const [skipReferenceValidation, setSkipReferenceValidation] = useState(false);

  const normalizedSource = normalizeTreePath(path);
  const normalizedTarget = normalizeTreePath(targetPath);

  const isMove = mode === "move";

  useEffect(() => {
    if (!open) return;
    setTargetPath("");
    setTagToCopy("latest");
    setSkipReferenceValidation(false);
  }, [open, path]);

  const targetError = targetPath.trim()
    ? validateRelocationTargetPath(path, targetPath, isMove ? "move" : "copy")
    : undefined;

  const refreshAfterRelocation = async () => {
    await refreshTreeQueries(qc, namespace, path, normalizedTarget);
    void qc.invalidateQueries({ queryKey: ["can-i", namespace] });
    void qc.removeQueries({ queryKey: ["item", namespace, path] });
    void qc.removeQueries({ queryKey: ["versions", namespace, path] });
  };

  const moveMut = useMutation({
    mutationFn: () =>
      treeApi.move(
        namespace,
        path,
        { target_path: normalizedTarget },
        {
          skip_reference_validation: skipReferenceValidation,
        },
      ),
    onSuccess: async () => {
      await refreshAfterRelocation();
      showToast(`Moved "${path}" to "${normalizedTarget}"`);
      onClose();
      navigate(`/ns/${namespace}/configs/${normalizedTarget}`);
    },
    onError: (e: Error) => pushApiError("Move failed", e),
  });

  const copyMut = useMutation({
    mutationFn: () => {
      const tag = tagToCopy.trim() || "latest";
      return treeApi.copy(
        namespace,
        path,
        { target_path: normalizedTarget },
        {
          tag_to_copy: tag,
          skip_reference_validation: skipReferenceValidation,
        },
      );
    },
    onSuccess: async () => {
      await refreshAfterRelocation();
      showToast(`Copied "${path}" to "${normalizedTarget}"`);
      onClose();
      navigate(`/ns/${namespace}/configs/${normalizedTarget}`);
    },
    onError: (e: Error) => pushApiError("Copy failed", e),
  });

  const pending = moveMut.isPending || copyMut.isPending;
  const title = isMove ? "Move item" : "Copy item";
  const actionLabel = isMove ? "Move" : "Copy";

  const handleSubmit = () => {
    if (targetError) return;
    if (isMove) moveMut.mutate();
    else copyMut.mutate();
  };

  const tagOptions = [
    "latest",
    ...tags.map((t) => t.name).filter((name) => name !== "latest"),
  ];
  const itemName = pathSegments(normalizedSource).at(-1) ?? normalizedSource;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      size="md"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            loading={pending}
            disabled={!!targetError}
            onClick={handleSubmit}
          >
            {actionLabel}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {isMove ? "Move" : "Copy"}{" "}
          <strong className="font-mono">{path}</strong> in namespace{" "}
          <strong className="font-mono">{namespace}</strong> to a new path.
        </p>

        <PathSearchCombobox
          namespace={namespace}
          value={targetPath}
          label="Destination path"
          inputId="relocation-destination-path"
          placeholder="folder/item-name"
          error={targetPath.trim() ? targetError : undefined}
          autoFocus
          filterItem={(item) => item.type === "folder"}
          emptyMessage="No matching folders"
          sanitizeInput={filterTreePathInput}
          queryKeySuffix="folder-combobox"
          onInputChange={setTargetPath}
          onSelect={(folder) => {
            setTargetPath(
              buildDestinationPathFromFolder(folder.path, itemName),
            );
          }}
        />

        {isMove && MOVE_WARNING_TYPES.has(type) && (
          <div className="flex gap-2 rounded-md border border-yellow-300 bg-yellow-50 px-3 py-2 text-xs text-yellow-800 dark:border-yellow-800/60 dark:bg-yellow-900/20 dark:text-yellow-300">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <ul className="list-disc space-y-1 pl-4">
              <li>
                Relative paths in{" "}
                <span className="font-mono">{configMetadataKey}</span> blocks
                (extend, render, validation schema, secrets, etc.) are resolved
                from this item&apos;s folder and may break after the move
                {type === "folder"
                  ? ", including configs inside this folder"
                  : ""}
                . Review dependent configs before confirming.
              </li>
              <li>
                Resolve statistics are keyed by path and do not carry over after
                a move — the chart will be empty until new resolve activity is
                recorded at the destination path.
              </li>
            </ul>
          </div>
        )}

        {!isMove && showsCopyTagField(type, isMove) && (
          <div className="space-y-1">
            <label
              htmlFor="tag-to-copy"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Version tag to copy
            </label>
            {type === "folder" ? (
              <Input
                id="tag-to-copy"
                value={tagToCopy}
                onChange={(e) => setTagToCopy(e.target.value)}
                placeholder="latest"
                className="font-mono"
              />
            ) : (
              <select
                id="tag-to-copy"
                value={tagToCopy}
                onChange={(e) => setTagToCopy(e.target.value)}
                className="block w-full rounded-md border border-slate-400 bg-surface-elevated px-3 py-1.5 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
              >
                {tagOptions.map((tag) => (
                  <option key={tag} value={tag}>
                    {tag}
                  </option>
                ))}
              </select>
            )}
            <p className="text-xs text-gray-400">
              {type === "folder"
                ? "Applied to every config and template in the folder. Copy fails if any item lacks this tag."
                : "Only the version at this tag is copied to the destination."}
            </p>
          </div>
        )}

        {REFERENCE_VALIDATION_TYPES.has(type) && (
          <label className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-300">
            <input
              type="checkbox"
              checked={skipReferenceValidation}
              onChange={(e) => setSkipReferenceValidation(e.target.checked)}
              className="mt-0.5 rounded"
            />
            <span>
              Skip reference validation
              <span className="mt-0.5 block text-xs text-gray-400">
                {isMove
                  ? "Do not verify that extend, render, schema, or secret references would still resolve at the destination path after the move."
                  : "Do not verify that extend, render, schema, or secret references exist at the destination. Use when copying a folder whose configs reference each other."}
              </span>
            </span>
          </label>
        )}

        {normalizedTarget && (
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {ITEM_TYPE_LABELS[type]}{" "}
            <span className="font-mono font-medium text-gray-800 dark:text-gray-200">
              {itemName}
            </span>{" "}
            will be available as{" "}
            <span className="font-mono font-medium text-gray-800 dark:text-gray-200">
              {normalizedTarget}
            </span>
            .
          </p>
        )}
      </div>
    </Modal>
  );
}
