import { env } from 'process';

import { useEmbeddedWithinIframe } from './embed';

export function useConsumerModeEnabled() {
  const { embedded } = useEmbeddedWithinIframe();
  const consumerModeEnabled = env.NEXT_PUBLIC_CONSUMER_MODE || embedded;
  return { consumerModeEnabled, embedded };
}
