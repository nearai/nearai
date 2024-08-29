import { useParams } from 'next/navigation';

import { type RegistryCategory } from '~/server/api/routers/hub';
import { api } from '~/trpc/react';

export function useResourceParams() {
  const { namespace, name, version } = useParams();

  return {
    namespace: namespace as string,
    name: name as string,
    version: version as string,
  };
}

export function useCurrentResource(category: RegistryCategory) {
  const { namespace, name, version } = useResourceParams();

  const list = api.hub.listRegistry.useQuery({
    category,
    namespace,
    showLatestVersion: false,
  });

  const currentVersions = list.data?.filter((item) => item.name === name);

  const currentResource = currentVersions?.find(
    (item) => item.version === version,
  );

  return {
    currentResource,
    currentVersions,
  };
}
