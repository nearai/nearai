import Link from "next/link";
import { Button } from "~/components/ui/button";
import { Three } from "~/components/ui/typography";

export function Navigation() {
  return (
    <div className="flex min-h-[100vh] min-w-[20%] flex-col gap-3 border-r-2 px-4">
      <Three>AI Hub</Three>
      <div className="flex flex-col gap-3">
        <NavigationItem name="Home" link="" />
        <NavigationItem name="Chat" link="" />
        <NavigationItem name="Models" link="models" />
        <NavigationItem name="Data" link="data" />
        <NavigationItem name="Settings" link="settings" />
      </div>
    </div>
  );
}

function NavigationItem({ name, link }: { name: string; link: string }) {
  return (
    <Button variant={"outline"} className="justify-start" asChild>
      <Link href={`/${link}`}>{name}</Link>
    </Button>
  );
}
