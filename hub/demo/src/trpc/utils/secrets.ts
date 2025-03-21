import { env } from 'process';

import { entrySecretModel } from '@/lib/models';
import { type AppRouterInputs } from '@/trpc/router';
import { createZodFetcher } from '@/utils/zod-fetch';

const fetchWithZod = createZodFetcher();

export async function conditionallyRemoveSecret(
  authorization: string,
  input: AppRouterInputs['hub']['addSecret'],
) {
  try {
    const secretsUrl = new URL(`${env.ROUTER_URL}/get_user_secrets`);
    secretsUrl.searchParams.append('limit', '10000');

    const secrets = await fetchWithZod(
      entrySecretModel.array(),
      secretsUrl.toString(),
      {
        headers: {
          Authorization: authorization,
        },
      },
    );

    const existingSecret = secrets.find(
      (secret) =>
        secret.key === input.key &&
        secret.namespace === input.namespace &&
        secret.name === input.name &&
        secret.version === input.version,
    );

    if (existingSecret) {
      const removeUrl = `${env.ROUTER_URL}/remove_hub_secret`;

      await fetch(removeUrl, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: authorization,
        },
        method: 'POST',
        body: JSON.stringify(input),
      });
    }
  } catch (error) {
    console.error('Failed to conditionally remove secret', error);
  }
}
