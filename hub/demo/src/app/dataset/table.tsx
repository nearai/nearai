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
  const listDataset = api.hub.listDataset.useQuery({ category: category });

  if (listDataset.data === undefined) {
    return <div>Loading...</div>;
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
          {listDataset.data.map((dataset) => (
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
