import { createContext, useContext } from 'react';
import { type z } from 'zod';

import type { ExtendedMessage } from '@/hooks/threads';
import { type threadMessageContentModel } from '@/lib/models';

type ThreadMessageContent = {
  content: z.infer<typeof threadMessageContentModel>;
  message: ExtendedMessage;
  messageContentId: string;
};

const ThreadMessageContext = createContext<ThreadMessageContent | null>(null);

export const ThreadMessageContentProvider = ThreadMessageContext.Provider;

export function useThreadMessageContent() {
  const context = useContext(ThreadMessageContext);

  if (!context)
    throw new Error(
      'ThreadMessageContent context was not found within useThreadMessageContent(). Make sure to wrap this component with <ThreadMessageContentProvider>',
    );

  return context;
}
