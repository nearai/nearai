import { One } from "~/components/ui/typography";
import RegistryTable from "./table";

export default function Data() {
  return (
    <div className="flex flex-col gap-2 px-24 py-4">
      <One>Datasets</One>
      <RegistryTable category="dataset" />
    </div>
  );
}
