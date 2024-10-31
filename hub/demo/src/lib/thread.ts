import { type z } from 'zod';

import { type threadMessageModel } from './models';

export function returnOptimisticThreadMessage(
  threadId: string,
  content: string,
) {
  const message: z.infer<typeof threadMessageModel> = {
    attachments: [],
    completed_at: null,
    content: [
      {
        text: {
          annotations: [],
          value: content,
        },
        type: '',
      },
    ],
    created_at: Date.now(),
    id: crypto.randomUUID(),
    incomplete_at: null,
    object: '',
    run_id: null,
    status: '',
    thread_id: threadId,
    role: 'user',
  };

  return message;
}
