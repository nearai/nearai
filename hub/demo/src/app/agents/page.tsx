import { One } from "~/components/ui/typography";
import RegistryTable from "../datasets/table";

export default function Data() {
  return (
    <div className="flex flex-col gap-2 px-24 py-4">
      <One>Agents</One>
      <RegistryTable category="agent" />
    </div>
  );
}
