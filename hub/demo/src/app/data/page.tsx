import { One } from "~/components/ui/typography";
import DatasetTable from "./table";

export default function Data() {
  return (
    <div className="flex flex-col gap-2 px-24 py-4">
      <One>Data</One>
      <DatasetTable />
    </div>
  );
}
