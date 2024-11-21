import { type z } from 'zod';
import { create, type StateCreator } from 'zustand';
import { devtools } from 'zustand/middleware';

import {
  type chatWithAgentModel,
  type threadFileModel,
  type threadMessageModel,
  type threadModel,
  type threadRunModel,
} from '~/lib/models';
import { type RouterOutputs } from '~/trpc/react';

type Thread = z.infer<typeof threadModel> & {
  run?: z.infer<typeof threadRunModel>;
  filesByName: Record<string, z.infer<typeof threadFileModel>>;
  messagesById: Record<string, z.infer<typeof threadMessageModel>>;
  latestMessageId?: string;
  latestRunId?: string;
};

type ThreadsStore = {
  optimisticMessages: {
    index: number;
    data: z.infer<typeof threadMessageModel>;
  }[];
  threadsById: Record<string, Thread>;
  addOptimisticMessages: (
    currentThreadId: string | null | undefined,
    inputs: z.infer<typeof chatWithAgentModel>[],
  ) => void;
  reset: () => void;
  setThread: (
    thread: Partial<Omit<RouterOutputs['hub']['thread'], 'id'>> & {
      id: string;
    },
  ) => void;
};

const store: StateCreator<ThreadsStore> = (set, get) => ({
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
          attachments: [],
          completed_at: null,
          content: [
            {
              text: {
                annotations: [],
                value: input.new_message,
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
          thread_id: currentThreadId ?? '',
          role: 'user',
        },
      });
    });

    set({ optimisticMessages });
  },

  reset: () => set({ optimisticMessages: [] }),

  setThread: ({ messages, files, run, ...data }) => {
    const threadsById = {
      ...get().threadsById,
    };

    const existingThread = threadsById[data.id];

    const updatedThread: Thread = {
      created_at: 0,
      metadata: {},
      object: '',
      ...data,
      run: run ?? existingThread?.run,
      filesByName: existingThread?.filesByName ?? {},
      messagesById: existingThread?.messagesById ?? {},
    };
    messages?.forEach((message) => {
      updatedThread.messagesById[message.id] = message;
    });
    files?.forEach((file) => {
      updatedThread.filesByName[file.filename] = file;
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
