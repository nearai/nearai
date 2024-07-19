import { useQuery } from "@tanstack/react-query";
import { api } from "~/trpc/react";

export function useListModels() {
  const listModels = api.router.listModels.useQuery();

  return useQuery({
    queryKey: ["listModels"],
    queryFn: () => {
      const m = listModels.data?.data.map((m) => {
        return { label: m.id, value: m.id };
      });

      return m;
    },
    enabled: !!listModels.data,
  });
}
