import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageSquareReply, Pencil, Reply, Trash2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { changeRequestsApi } from "../../api/changeRequests";
import type { ChangeRequest, ChangeRequestComment } from "../../api/types";
import { mergeDiscussionTimeline } from "../../lib/changeRequestActivity";
import { useAuth } from "../../auth/useAuth";
import { Button } from "../ui/Button";
import { ChangeRequestLineRefMarkdown } from "./ChangeRequestLineRefMarkdown";
import { MarkdownEditor } from "../ui/MarkdownEditor";
import { formatUserDateTime } from "../../lib/datetime";
import { pushApiError } from "../../store/notifications";
import { cn } from "../ui/cn";
import { changeRequestRefetchInterval } from "../../lib/changeRequestLiveSync";

function commentsQueryKey(namespace: string, path: string, number: number) {
  return ["change-request-comments", namespace, path, number] as const;
}

function quoteComment(body: string): string {
  const quoted = body
    .split("\n")
    .map((line) => `> ${line}`)
    .join("\n");
  return `${quoted}\n\n`;
}

type ReplyTarget = "thread" | number;

export function ChangeRequestDiscussion({
  namespace,
  path,
  number,
  onLineRefClick,
  canComment,
  changeRequest,
  pageActive,
}: {
  namespace: string;
  path: string;
  number: number;
  pageActive: boolean;
  onLineRefClick: (hashFragment: string) => void;
  /** False when the change request is no longer open (read-only discussion). */
  canComment: boolean;
  changeRequest: ChangeRequest;
}) {
  const qc = useQueryClient();
  const { whoami } = useAuth();
  const [replyTarget, setReplyTarget] = useState<ReplyTarget | null>(null);
  const [commentBody, setCommentBody] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editBody, setEditBody] = useState("");

  const actorId = useMemo(() => {
    if (!whoami) return "";
    return whoami.display_name ?? whoami.identifier ?? "";
  }, [whoami]);

  useEffect(() => {
    if (!canComment) {
      setReplyTarget(null);
      setCommentBody("");
      setEditingId(null);
      setEditBody("");
    }
  }, [canComment]);

  const {
    data: commentsData,
    isError,
    error,
  } = useQuery({
    queryKey: commentsQueryKey(namespace, path, number),
    queryFn: () => changeRequestsApi.listComments(namespace, path, number),
    refetchInterval: changeRequestRefetchInterval(
      changeRequest.status,
      pageActive,
    ),
    refetchIntervalInBackground: false,
  });

  const comments = commentsData?.items ?? [];

  const timeline = useMemo(
    () => mergeDiscussionTimeline(comments, changeRequest),
    [comments, changeRequest],
  );

  const invalidateComments = useCallback(() => {
    void qc.invalidateQueries({
      queryKey: commentsQueryKey(namespace, path, number),
    });
  }, [qc, namespace, path, number]);

  const commentMut = useMutation({
    mutationFn: () =>
      changeRequestsApi.addComment(namespace, path, number, commentBody),
    onSuccess: (created) => {
      setCommentBody("");
      setReplyTarget(null);
      qc.setQueryData(
        commentsQueryKey(namespace, path, number),
        (
          prev: { items: ChangeRequestComment[]; total: number } | undefined,
        ) => {
          if (!prev) {
            return { items: [created], total: 1 };
          }
          const exists = prev.items.some((c) => c.id === created.id);
          if (exists) return prev;
          return {
            ...prev,
            items: [...prev.items, created],
            total: prev.total + 1,
          };
        },
      );
      invalidateComments();
    },
    onError: (e: Error) => pushApiError("Comment failed", e),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, body }: { id: number; body: string }) =>
      changeRequestsApi.updateComment(namespace, path, number, id, body),
    onSuccess: () => {
      setEditingId(null);
      setEditBody("");
      invalidateComments();
    },
    onError: (e: Error) => pushApiError("Failed to update comment", e),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) =>
      changeRequestsApi.deleteComment(namespace, path, number, id),
    onSuccess: () => invalidateComments(),
    onError: (e: Error) => pushApiError("Failed to delete comment", e),
  });

  const submitNewComment = useCallback(() => {
    if (!commentBody.trim() || commentMut.isPending) return;
    commentMut.mutate();
  }, [commentBody, commentMut]);

  const submitEdit = useCallback(() => {
    if (editingId === null || !editBody.trim() || updateMut.isPending) return;
    updateMut.mutate({ id: editingId, body: editBody });
  }, [editingId, editBody, updateMut]);

  const openReply = (target: ReplyTarget, quoteFrom?: string) => {
    setEditingId(null);
    setEditBody("");
    setReplyTarget(target);
    setCommentBody(quoteFrom ? quoteComment(quoteFrom) : "");
  };

  const cancelReply = () => {
    setReplyTarget(null);
    setCommentBody("");
  };

  const startEdit = (c: ChangeRequestComment) => {
    setReplyTarget(null);
    setCommentBody("");
    setEditingId(c.id);
    setEditBody(c.body);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditBody("");
  };

  const handleDelete = (c: ChangeRequestComment) => {
    if (deleteMut.isPending) return;
    if (!window.confirm("Delete this comment? This cannot be undone.")) {
      return;
    }
    deleteMut.mutate(c.id);
  };

  return (
    <section className="space-y-3 p-4 text-xs">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
        Discussion
      </h2>
      {isError && (
        <p className="text-[11px] text-red-600 dark:text-red-400">
          Could not load comments
          {error instanceof Error && error.message ? `: ${error.message}` : ""}
        </p>
      )}
      <ul className="space-y-2">
        {timeline.map((entry) => {
          if (entry.kind === "activity") {
            return (
              <li
                key={entry.id}
                className="rounded border border-dashed border-gray-200 bg-slate-50/60 px-2 py-2 dark:border-gray-700 dark:bg-gray-900/30"
              >
                <p className="text-[11px] leading-snug text-gray-600 dark:text-gray-400">
                  <span className="text-gray-500 dark:text-gray-500">
                    {formatUserDateTime(entry.created_at)}
                  </span>{" "}
                  {entry.message}
                </p>
              </li>
            );
          }

          const c = entry.comment;
          const isOwner = Boolean(actorId && c.author === actorId);
          const isCrAuthor = c.author === changeRequest.created_by;
          const isEditing = editingId === c.id;

          return (
            <li
              key={`comment-${c.id}`}
              className={cn(
                "rounded border p-2",
                isCrAuthor
                  ? "border-brand-200/80 bg-brand-50/40 dark:border-brand-800/60 dark:bg-brand-950/25"
                  : "border-gray-100 dark:border-gray-800",
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="text-[11px] text-gray-500 dark:text-gray-400">
                  {c.author}
                  {isCrAuthor && (
                    <span className="ml-1.5 font-medium text-brand-700 dark:text-brand-400">
                      · Author
                    </span>
                  )}
                  <span className="text-gray-400 dark:text-gray-500">
                    {" "}
                    · {formatUserDateTime(c.created_at)}
                  </span>
                </div>
                <div className="flex shrink-0 items-center gap-0.5">
                  {canComment && (
                    <button
                      type="button"
                      className="rounded p-1 text-gray-500 hover:bg-slate-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
                      aria-label="Reply to comment"
                      onClick={() => openReply(c.id, c.body)}
                    >
                      <MessageSquareReply className="h-3.5 w-3.5" />
                    </button>
                  )}
                  {canComment && isOwner && !isEditing && (
                    <>
                      <button
                        type="button"
                        className="rounded p-1 text-gray-500 hover:bg-slate-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
                        aria-label="Edit comment"
                        onClick={() => startEdit(c)}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        className="rounded p-1 text-gray-500 hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-950/40 dark:hover:text-red-400"
                        aria-label="Delete comment"
                        onClick={() => handleDelete(c)}
                        disabled={deleteMut.isPending}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </>
                  )}
                </div>
              </div>
              {isEditing ? (
                <div className="mt-2 space-y-2">
                  <MarkdownEditor
                    value={editBody}
                    onChange={setEditBody}
                    rows={5}
                    placeholder="Edit comment…"
                    textareaClassName="text-xs"
                    disabled={updateMut.isPending}
                    onSubmit={submitEdit}
                  />
                  <div className="flex gap-2">
                    <Button
                      variant="primary"
                      size="sm"
                      loading={updateMut.isPending}
                      disabled={!editBody.trim()}
                      onClick={submitEdit}
                    >
                      Save
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={cancelEdit}
                      disabled={updateMut.isPending}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <ChangeRequestLineRefMarkdown
                  className="mt-1 text-gray-700 dark:text-gray-300"
                  onLineRefClick={onLineRefClick}
                >
                  {c.body}
                </ChangeRequestLineRefMarkdown>
              )}
            </li>
          );
        })}
      </ul>

      {canComment && replyTarget !== null ? (
        <div className="space-y-2">
          <p className="text-[11px] font-medium text-gray-600 dark:text-gray-400">
            {typeof replyTarget === "number" ? "Reply" : "New comment"}
          </p>
          <MarkdownEditor
            value={commentBody}
            onChange={setCommentBody}
            rows={5}
            placeholder="Write a comment (Markdown supported)…"
            textareaClassName="text-xs"
            disabled={commentMut.isPending}
            onSubmit={submitNewComment}
          />
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              loading={commentMut.isPending}
              disabled={!commentBody.trim()}
              onClick={submitNewComment}
            >
              Post
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={cancelReply}
              disabled={commentMut.isPending}
            >
              Cancel
            </Button>
            <span className="text-[10px] text-gray-400 dark:text-gray-500">
              Ctrl+Enter to post
            </span>
          </div>
        </div>
      ) : canComment ? (
        <Button
          variant="secondary"
          size="sm"
          onClick={() => openReply("thread")}
        >
          <Reply className="mr-1.5 h-3.5 w-3.5" aria-hidden />
          Reply
        </Button>
      ) : null}
    </section>
  );
}
