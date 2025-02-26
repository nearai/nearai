import { Accordion, Dialog, Flex, SvgIcon, Text } from '@near-pagoda/ui';
import { Code as CodeIcon } from '@phosphor-icons/react';
import { type z } from 'zod';

import { useCurrentEntryParams } from '~/hooks/entries';
import { primaryUrlForEntry } from '~/lib/entries';
import { type entryModel } from '~/lib/models';

import { Code } from './lib/Code';
import { InlineCode } from './lib/InlineCode';

type Props = {
  entry: z.infer<typeof entryModel> | undefined;
  isOpen: boolean;
  setIsOpen: (open: boolean) => unknown;
};

export const EmbedAgentModal = ({ entry, isOpen, setIsOpen }: Props) => {
  const { id } = useCurrentEntryParams();

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

              <Flex direction="column" gap="m">
                <Text>
                  Copy and paste the following HTML to embed this agent on any
                  website:
                </Text>

                <Code
                  language="html"
                  source={`<iframe 
  src="https://app.near.ai/embed/${id}" 
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
                    Customize
                  </Accordion.Trigger>

                  <Accordion.Content>
                    <Text>
                      You can customize how an agent is displayed by updating
                      its <InlineCode>metadata.json</InlineCode>:
                    </Text>

                    <Code
                      language="json"
                      source={`{
  "details": {
    "agent": {
      "embed": {
        "logo": "https://near.ai/logo-white.svg"
      }
    }
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
