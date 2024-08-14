"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "~/components/ui/table";
import { api } from "~/trpc/react";

export default function RegistryTable({ category }: { category: string }) {
  const listRegistry = api.hub.listRegistry.useQuery({ category: category });

  if (listRegistry.isLoading) {
    return <div>Loading...</div>;
  }

  if (listRegistry.error) {
    return <div>Error: {listRegistry.error.message}</div>;
  }

  if (listRegistry.data?.length === 0) {
    return <div>No data</div>;
  }

  return (
    <div className="rounded border">
      <Table>
        <TableHeader className="bg-gray-50">
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Namespace</TableHead>
            <TableHead>Version</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {listRegistry.data?.map((dataset) => (
            <TableRow key={dataset.name + dataset.namespace + dataset.version}>
              <TableCell className="font-medium">{dataset.name}</TableCell>
              <TableCell>{dataset.namespace}</TableCell>
              <TableCell>{dataset.version}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
