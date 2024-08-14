"use client";

import { Chat } from "./_components/chat";
import HydrationZustand from "./_components/hydration";

export default function Home() {
  return (
    <HydrationZustand>
      <Chat />
    </HydrationZustand>
  );
}
