import { type z } from 'zod';
import { create, type StateCreator } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

import { idForEntry } from '@/lib/entries';
import { type entryModel } from '@/lib/models';

type AgentSettings = Partial<{
  allowRemoteRunCallsToOtherAgents: boolean;
  allowWalletTransactionRequests: boolean;
}>;

type AgentSettingsStore = {
  agentSettingsById: Record<string, AgentSettings>;
  getAgentSettings: (agent: z.infer<typeof entryModel>) => AgentSettings;
  setAgentSettings: (
    agent: z.infer<typeof entryModel>,
    settings: AgentSettings,
  ) => void;
};

const createStore: StateCreator<AgentSettingsStore> = (set, get) => ({
  agentSettingsById: {},

  getAgentSettings: (agent: z.infer<typeof entryModel>) => {
    const id = idForEntry(agent);
    return get().agentSettingsById[id] ?? {};
  },

  setAgentSettings: (
    agent: z.infer<typeof entryModel>,
    settings: AgentSettings,
  ) => {
    const agentSettingsById = {
      ...get().agentSettingsById,
    };

    const id = idForEntry(agent);

    agentSettingsById[id] = {
      ...agentSettingsById[id],
      ...settings,
    };

    set({ agentSettingsById });
  },
});

const name = 'AgentSettingsStore';

export const useAgentSettingsStore = create<AgentSettingsStore>()(
  devtools(persist(createStore, { name, skipHydration: true }), {
    name,
  }),
);
