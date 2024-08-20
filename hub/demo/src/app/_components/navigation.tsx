"use client";

import {
  BookOpenCheck,
  Bot,
  Database,
  FileBox,
  MessageCircle,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { Button } from "~/components/ui/button";
import { Three } from "~/components/ui/typography";
import usePersistingStore from "~/store/store";
import HydrationZustand from "./hydration";
import { NearLogin } from "./near";

export function Navigation() {
  const store = usePersistingStore();

  return (
    <HydrationZustand>
      <div className="flex h-screen w-64 flex-col justify-between gap-3 overflow-y-auto border-r-2 px-4 py-4">
        <div>
          <Three>AI Hub</Three>
          <div className="flex flex-col justify-between">
            <div className="flex flex-col gap-3">
              {/* <NavigationItem name="Home" link="" /> */}
              <NavigationItem
                name="Chat"
                link=""
                icon={<MessageCircle className="mr-2 h-4 w-4" />}
              />
              <NavigationItem
                name="Models"
                link="models"
                icon={<FileBox className="mr-2 h-4 w-4" />}
              />
              <NavigationItem
                name="Datasets"
                link="datasets"
                icon={<Database className="mr-2 h-4 w-4" />}
              />
              <NavigationItem
                name="Benchmarks"
                link="benchmarks"
                icon={<BookOpenCheck className="mr-2 h-4 w-4" />}
              />
              <NavigationItem
                name="Agents"
                link="agents"
                icon={<Bot className="mr-2 h-4 w-4" />}
              />
              <NavigationItem
                name="Settings"
                link="settings"
                icon={<Settings className="mr-2 h-4 w-4" />}
              />
            </div>
          </div>
        </div>
        <div className="flex flex-col gap-3">
          {store.isAuthenticated() && (
            <Button
              className="w-full"
              onClick={() => {
                store.clearAuth();
              }}
              type="button"
            >
              Sign Out
            </Button>
          )}
          {!store.isAuthenticated() && <NearLogin />}

          <Link
            className="self-center text-xs underline"
            href="/terms-and-conditions.pdf"
            target="_blank"
          >
            Terms & Conditions
          </Link>
        </div>
      </div>
    </HydrationZustand>
  );
}

function NavigationItem({
  name,
  link,
  icon,
}: {
  name: string;
  link: string;
  icon: React.ReactNode;
}) {
  return (
    <Button variant={"ghost"} className="justify-start lg:w-[200px]" asChild>
      <Link href={`/${link}`}>
        <div className="inline-flex items-center">
          {icon}
          {name}
        </div>
      </Link>
    </Button>
  );
}
