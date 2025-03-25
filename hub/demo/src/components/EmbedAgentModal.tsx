import { Accordion, Checkbox, Dialog, Flex, SvgIcon, Text } from '@nearai/ui';
import { Code as CodeIcon } from '@phosphor-icons/react';
import { useState } from 'react';
import { type z } from 'zod';

import { useCurrentEntryParams } from '@/hooks/entries';
import { primaryUrlForEntry } from '@/lib/entries';
import { type entryModel } from '@/lib/models';

import { Code } from './lib/Code';
import { InlineCode } from './lib/InlineCode';

type Props = {
  entry: z.infer<typeof entryModel> | undefined;
  isOpen: boolean;
  setIsOpen: (open: boolean) => unknown;
};

export const EmbedAgentModal = ({ entry, isOpen, setIsOpen }: Props) => {
  const { id } = useCurrentEntryParams();
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  if (entry && entry.category !== 'agent') {
    throw new Error(
      `Attempted to render ${entry.category} with <EmbedAgentModal />`,
    );
  }

  return (
    <>
      {entry && (
        <Dialog.Root open={isOpen} onOpenChange={setIsOpen}>
          <Dialog.Content title="Embed Agent" size="m">
            <Flex direction="column" gap="l">
              <Flex align="center" gap="s">
                <SvgIcon icon={<CodeIcon />} color="sand-9" />
                <Text href={primaryUrlForEntry(entry)} target="_blank">
                  {id}
                </Text>
              </Flex>

              <Flex direction="column" gap="s">
                <Text size="text-xs" weight={600} uppercase>
                  Theme
                </Text>
                <Flex align="center" gap="m">
                  <Flex as="label" align="center" gap="s">
                    <Checkbox
                      name="theme"
                      value="light"
                      type="radio"
                      checked={theme === 'light'}
                      onChange={() => setTheme('light')}
                    />
                    Light
                  </Flex>

                  <Flex as="label" align="center" gap="s">
                    <Checkbox
                      name="theme"
                      value="dark"
                      type="radio"
                      checked={theme === 'dark'}
                      onChange={() => setTheme('dark')}
                    />
                    Dark
                  </Flex>
                </Flex>
              </Flex>

              <Flex direction="column" gap="m">
                <Text>
                  Copy and paste the following HTML to embed this agent on any
                  website:
                </Text>

                <Code
                  language="html"
                  source={`<iframe 
  src="https://app.near.ai/embed/${id}?theme=${theme}" 
  sandbox="allow-scripts allow-popups allow-same-origin allow-forms"
  style="border: none; height: 100svh;">
</iframe>`}
                />

                <Text size="text-s"></Text>
              </Flex>

              <Accordion.Root type="multiple">
                <Accordion.Item value="customize">
                  <Accordion.Trigger
                    style={{ width: 'auto', gap: 'var(--gap-s)' }}
                  >
                    Customize Metadata
                  </Accordion.Trigger>

                  <Accordion.Content>
                    <Text>
                      You can further customize how an agent is displayed by
                      updating its <InlineCode>metadata.json</InlineCode>:
                    </Text>

                    <Code
                      language="json"
                      source={`{
  "details": {
    "agent": {
      "embed": {
        "logo": "https://images.com/logo.svg" | false
      },
      "welcome": {
        "title": "Helpful Assistant",
        "description": "How can I help you today?"
      }
    },
    "icon": "https://images.com/icon.svg"
  }
}`}
                    />
                  </Accordion.Content>
                </Accordion.Item>
              </Accordion.Root>
            </Flex>
          </Dialog.Content>
        </Dialog.Root>
      )}
    </>
  );
};
