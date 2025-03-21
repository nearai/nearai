# TRPC + React Query

This setup was implemented following this guide to support server components and client components in the Next JS App Router: https://trpc.io/docs/client/react/server-components

## Usage in client components

```tsx
'use client';

import { trpc } from '@/trpc/TRPCProvider';

export const MyClientComponent = () => {
  const agentsQuery = trpc.hub.entries.useQuery({
    category: 'agent',
  });

  return <div>{agentsQuery.data}</div>;
};
```

## Usage in server components

```tsx
import { trpc } from '@/trpc/server';

export const MyServerComponent = async () => {
  const agents = await trpc.hub.entries.useQuery({
    category: 'agent',
  });

  return <div>{agents}</div>;
};
```
