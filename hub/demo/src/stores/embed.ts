import type { NearAiUiProvider } from '@nearai/ui';
import type { ComponentProps } from 'react';
import { create, type StateCreator } from 'zustand';
import { devtools } from 'zustand/middleware';

export type Theme = NonNullable<
  ComponentProps<typeof NearAiUiProvider>['value']
>['forcedTheme'];

type EmbedStore = {
  forcedTheme?: Theme;
  setForcedTheme: (forcedTheme: Theme) => void;
};

const store: StateCreator<EmbedStore> = (set) => ({
  forcedTheme: undefined,

  setForcedTheme: (forcedTheme) => {
    set({ forcedTheme });
  },
});

export const name = 'EmbedStore';

export const useEmbedStore = create<EmbedStore>()(devtools(store, { name }));
