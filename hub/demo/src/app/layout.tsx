import "~/styles/globals.css";

import { GeistSans } from "geist/font/sans";

import { TRPCReactProvider } from "~/trpc/react";
import { Navigation } from "./_components/navigation";

export const metadata = {
  title: "AI Hub",
  description: "NEAR AI Hub",
  icons: [{ rel: "icon", url: "/favicon.ico" }],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${GeistSans.variable}`}>
      <body>
        <TRPCReactProvider>
          <main>
            <div className="flex h-full w-full">
              <Navigation />
              <div className="flex-grow">{children}</div>
            </div>
          </main>
        </TRPCReactProvider>
      </body>
    </html>
  );
}
