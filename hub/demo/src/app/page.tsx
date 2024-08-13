"use client";

import { Chat } from "./_components/chat";
import HydrationZustand from "./_components/hydration";

export default function Home() {
  return (
    <main>
      <HydrationZustand>
        <Chat />
      </HydrationZustand>
    </main>
  );
}
