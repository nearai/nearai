import { type z } from 'zod';
import { createZodFetcher } from 'zod-fetch';

import { env } from '~/env';
import { type chatWithAgentModel, runModel, threadModel } from '~/lib/models';
import { poll } from '~/utils/poll';

const fetchWithZod = createZodFetcher();

export async function runMessageOnAgentThread(
  authorization: string,
  input: z.infer<typeof chatWithAgentModel>,
) {
  const thread = input.thread_id
    ? await fetchWithZod(
        threadModel,
        `${env.ROUTER_URL}/threads/${input.thread_id}`,
        {
          headers: {
            Authorization: authorization,
          },
        },
      )
    : await fetchWithZod(threadModel, `${env.ROUTER_URL}/threads`, {
        method: 'POST',
        headers: {
          Authorization: authorization,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });

  await fetch(`${env.ROUTER_URL}/threads/${thread.id}/messages`, {
    method: 'POST',
    headers: {
      Authorization: authorization,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      content: input.new_message,
      role: 'user',
    }),
  });

  const createdRun = await fetchWithZod(
    runModel,
    `${env.ROUTER_URL}/threads/${thread.id}/runs`,
    {
      method: 'POST',
      headers: {
        Authorization: authorization,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        thread_id: thread.id,
        assistant_id: input.agent_id,
        instructions: 'You are a helpful assistant. Complete the given task.',
        model: 'fireworks::accounts/fireworks/models/llama-v3p1-405b-instruct',
      }),
    },
  );

  await poll(
    `${env.ROUTER_URL}/threads/${thread.id}/runs/${createdRun.id}`,
    {
      headers: {
        Authorization: authorization,
        'Content-Type': 'application/json',
      },
    },
    {
      attemptDelayMs: 300,
      maxAttempts: 400,
      // 2 minutes of polling...
    },
    async (response, currentAttempt) => {
      const data = (await response.json()) as unknown;

      if (env.NODE_ENV === 'development') {
        // When running locally, this log statement can be useful
        console.log(`Polling thread run - attempt ${currentAttempt}`, data);
      }

      const run = runModel.parse(data);
      if (run.status !== 'in_progress' && run.status !== 'queued') {
        return run;
      }
    },
  );

  return {
    threadId: thread.id,
  };
}
