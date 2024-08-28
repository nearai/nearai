import { useParams } from 'next/navigation';

import { type RegistryCategory } from '~/server/api/routers/hub';
import { api } from '~/trpc/react';

export function useResourceParams() {
  const { accountId, name, version } = useParams();

  return {
    accountId: accountId as string,
    name: name as string,
    version: version as string,
  };
}

export function useCurrentResource(category: RegistryCategory) {
  const { accountId, name, version } = useParams();
  const list = api.hub.listRegistry.useQuery({ category });
  const currentResource = list.data?.find(
    (item) =>
      item.namespace === accountId &&
      item.name === name &&
      item.version === version,
  );

  return {
    currentResource,
  };
}
