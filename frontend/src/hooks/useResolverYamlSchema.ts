import { useQuery } from "@tanstack/react-query";
import { fetchResolverConfigurationSchema } from "../api/schema";

export function useResolverYamlSchema() {
  const schemaQuery = useQuery({
    queryKey: ["resolver-configuration-schema"],
    queryFn: ({ signal }) => fetchResolverConfigurationSchema(signal),
    staleTime: Number.POSITIVE_INFINITY,
  });

  return {
    schema: schemaQuery.data ?? null,
    isReady: Boolean(schemaQuery.data),
  };
}
