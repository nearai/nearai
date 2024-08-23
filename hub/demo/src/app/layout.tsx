import '~/styles/globals.scss';

import { Footer } from '~/components/Footer';
import { Navigation } from '~/components/Navigation';
import { SignInHandler } from '~/components/SignInHandler';
import { ZustandHydration } from '~/components/ZustandHydration';
import { TRPCReactProvider } from '~/trpc/react';

import s from './layout.module.scss';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <title>AI Hub</title>
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, minimum-scale=1"
        />
        <meta name="description" content="NEAR AI Hub" />
        <link rel="icon" href="/favicon.ico" />
      </head>

      <body>
        <SignInHandler />
        <ZustandHydration />

        <TRPCReactProvider>
          <div className={s.wrapper}>
            <Navigation />
            <main className={s.main}>{children}</main>
            <Footer />
          </div>
        </TRPCReactProvider>
      </body>
    </html>
  );
}
