import { openToast } from '@near-pagoda/ui';

export function handleClientError({
  error,
  title,
  description,
}: {
  error: unknown;
  title?: string;
  description?: string;
}) {
  console.error(error);
  openToast({
    type: 'error',
    title: title ?? 'Unexpected Error',
    description: description ?? 'Please try again later',
  });
}
