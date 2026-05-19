import type { ReactNode } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { Spinner } from "./Spinner";
import { EmptyState } from "./EmptyState";

export function QueryBoundary<T>({
  query,
  children,
}: {
  query: UseQueryResult<T>;
  children: (data: T) => ReactNode;
}) {
  if (query.isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner />
      </div>
    );
  }
  if (query.error) {
    return (
      <EmptyState
        title="Something went wrong"
        description={(query.error as Error).message}
      />
    );
  }
  if (!query.data) return null;
  return <>{children(query.data)}</>;
}
