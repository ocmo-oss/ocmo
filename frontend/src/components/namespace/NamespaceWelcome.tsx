import { useQuery } from "@tanstack/react-query";
import { namespacesApi } from "../../api/namespaces";
import { DescriptionMarkdown } from "../ui/DescriptionMarkdown";
import { Skeleton } from "../ui/Skeleton";

interface NamespaceWelcomeProps {
  namespace: string;
}

export function NamespaceWelcome({ namespace }: NamespaceWelcomeProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["namespace", namespace],
    queryFn: ({ signal }) => namespacesApi.get(namespace, signal),
    staleTime: 30_000,
  });

  const hasDescription = Boolean(data?.description?.trim());

  if (isLoading) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-6">
        <div className="w-full max-w-lg space-y-6">
          <div className="space-y-2">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
          <Skeleton className="h-12 w-full rounded-md" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col items-center justify-center px-6">
      <div className="w-full max-w-lg space-y-6 text-left">
        {hasDescription && (
          <section>
            <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">
              Description
            </h2>
            <div className="rounded-md border border-slate-300 bg-surface px-4 py-3 dark:border-gray-700 dark:bg-gray-900/40">
              <DescriptionMarkdown className="text-sm text-gray-600 dark:text-gray-300">
                {data!.description}
              </DescriptionMarkdown>
            </div>
          </section>
        )}

        <p className="rounded-md border border-dashed border-slate-300 px-4 py-3 text-sm text-gray-400 dark:border-gray-700">
          Select an item from the tree to get started
        </p>
      </div>
    </div>
  );
}
