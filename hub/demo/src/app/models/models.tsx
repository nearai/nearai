"use client";

import { One } from "~/components/ui/typography";
import { api } from "~/trpc/react";
import ModelCard from "./modelCard";

export default function ListModels() {
  const listModels = api.hub.listModels.useQuery();

  return (
    <div className="px-24 py-4">
      <One>Models</One>
      <div className="grid grid-cols-1 gap-6 py-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {listModels.data?.data.map((model) => (
          <ModelCard key={model.id} model={model} />
        ))}
      </div>
    </div>
  );
}
