"use client";

import { One } from "~/components/ui/typography";
import ListNonces from "./nonces";

export default function Settings() {
  return (
    <div className="flex flex-col gap-4 px-24 py-4">
      <One>Settings</One>
      <ListNonces />
    </div>
  );
}
