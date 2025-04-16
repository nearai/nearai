import { type UseMutateAsyncFunction } from '@tanstack/react-query';
import { type z } from 'zod';
import { create, type StateCreator } from 'zustand';
import { devtools } from 'zustand/middleware';

import { type AgentChatMutationInput } from '@/components/AgentRunner';
import {
  type chatWithAgentModel,
  type threadFileModel,
  type threadMessageContentModel,
  type threadMessageModel,
  type threadModel,
  type threadRunModel,
} from '@/lib/models';
import { type AppRouterOutputs } from '@/trpc/router';
import { stringToPotentialJson } from '@/utils/string';

type Thread = z.infer<typeof threadModel> & {
  run?: z.infer<typeof threadRunModel>;
  filesById: Record<string, z.infer<typeof threadFileModel>>;
  messagesById: Record<string, z.infer<typeof threadMessageModel>>;
  latestMessageId?: string;
  latestRunId?: string;
};

type ThreadsStore = {
  addMessage?: UseMutateAsyncFunction<
    void,
    Error,
    AgentChatMutationInput,
    unknown
  >;
  openedFileId: string | null;
  optimisticMessages: {
    index: number;
    data: z.infer<typeof threadMessageModel>;
  }[];
  threadsById: Record<string, Thread>;
  addOptimisticMessages: (
    currentThreadId: string | null | undefined,
    inputs: z.infer<typeof chatWithAgentModel>[],
  ) => void;
  clearOptimisticMessages: () => void;
  setAddMessage: (addMessage: ThreadsStore['addMessage']) => void;
  setOpenedFileId: (openedFileId: string | null) => void;
  setThread: (
    thread: Partial<Omit<AppRouterOutputs['hub']['thread'], 'id'>> & {
      id: string;
    },
  ) => void;
};

const store: StateCreator<ThreadsStore> = (set, get) => ({
  addMessage: undefined,
  openedFileId: null,
  optimisticMessages: [],
  threadsById: {},

  addOptimisticMessages: (currentThreadId, inputs) => {
    const threadsById = {
      ...get().threadsById,
    };

    const existingThread = currentThreadId
      ? threadsById[currentThreadId]
      : undefined;

    const optimisticMessages = [...get().optimisticMessages];
    const messages = existingThread
      ? Object.values(existingThread.messagesById)
      : [];

    inputs.forEach((input, i) => {
      optimisticMessages.push({
        index: i + messages.length,
        data: {
          attachments: input.attachments || [],
          completed_at: null,
          content: [
            {
              text: {
                annotations: [],
                value: input.new_message,
              },
              type: 'text',
            },
          ],
          created_at: Date.now(),
          id: crypto.randomUUID(),
          incomplete_at: null,
          object: '',
          run_id: null,
          status: '',
          thread_id: currentThreadId ?? '',
          role: 'user',
        },
      });
    });

    set({ optimisticMessages });
  },

  clearOptimisticMessages: () => set({ optimisticMessages: [] }),

  setAddMessage: (addMessage) => set({ addMessage }),

  setOpenedFileId: (openedFileId) => set({ openedFileId }),

  setThread: ({ messages, files, run, ...data }) => {
    const threadsById = {
      ...get().threadsById,
    };

    const existingThread = threadsById[data.id];

    const updatedThread: Thread = {
      created_at: 0,
      metadata: { agent_ids: [], topic: '' },
      object: '',
      ...data,
      run: run ?? existingThread?.run,
      filesById: existingThread?.filesById ?? {},
      messagesById: existingThread?.messagesById ?? {},
    };
    messages?.forEach((message) => {
      updatedThread.messagesById[message.id] = message;
    });
    files?.forEach((file) => {
      updatedThread.filesById[file.id] = file;
    });

    const allMessages = Object.values(updatedThread.messagesById);
    const latestMessage = allMessages.at(-1);

    const optimisticMessages: ThreadsStore['optimisticMessages'] = [];
    get().optimisticMessages.forEach((message) => {
      if (message.index >= allMessages.length) {
        optimisticMessages.push(message);
      }
    });

    threadsById[updatedThread.id] = {
      ...updatedThread,
      latestMessageId: latestMessage?.id,
      latestRunId: run?.id ?? undefined,
    };

    set({ threadsById, optimisticMessages });
  },
});

const name = 'ThreadsStore';

export const useThreadsStore = create<ThreadsStore>()(
  devtools(store, {
    name,
  }),
);

export function useThreadMessageContentFilter<
  T = z.infer<typeof threadMessageContentModel>,
>(
  threadId: string,
  filter: (json: Record<string, unknown> | null, text: string) => T | undefined,
) {
  const threadsById = useThreadsStore((store) => store.threadsById);
  const thread = threadsById[threadId];
  const messages = thread?.messagesById
    ? Object.values(thread.messagesById)
    : [];
  const allContents = messages.flatMap((m) => m.content);
  const results: T[] = [];

  allContents.forEach((content) => {
    const match = filter(
      stringToPotentialJson(content.text?.value ?? ''),
      content.text?.value ?? '',
    );

    if (match) {
      results.push(match);
    }
  });

  return results;
}
