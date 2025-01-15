import {
  Button,
  Card,
  Dialog,
  Flex,
  SvgIcon,
  Text,
  Tooltip,
} from '@near-pagoda/ui';
import { DownloadSimple } from '@phosphor-icons/react';
import { type CSSProperties, useState } from 'react';
import { type z } from 'zod';

import { idForEntry } from '~/lib/entries';
import { type entryModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { toTitleCase } from '~/utils/string';

import { Code } from './lib/Code';

type Props = {
  entry: z.infer<typeof entryModel> | undefined;
  style?: CSSProperties;
};

export const DevelopButton = ({ entry, style }: Props) => {
  const accountId = useAuthStore((store) => store.auth?.account_id);
  const isPermittedToViewSource =
    !entry?.details.private_source || accountId === entry.namespace;
  const [forkModalIsOpen, setForkModalIsOpen] = useState(false);

  if (!isPermittedToViewSource) return null;

  return (
    <>
      <Tooltip
        asChild
        content={`View instructions to download and develop this ${entry?.category} locally`}
      >
        <Button
          label="Develop"
          iconLeft={<SvgIcon size="xs" icon={<DownloadSimple />} />}
          size="small"
          variant="affirmative"
          style={style}
          onClick={() => setForkModalIsOpen(true)}
        />
      </Tooltip>

      {entry && (
        <Dialog.Root open={forkModalIsOpen} onOpenChange={setForkModalIsOpen}>
          <Dialog.Content
            title={`Download & Develop ${toTitleCase(entry.category)}`}
            size="m"
          >
            <Flex direction="column" gap="l">
              <Flex direction="column" gap="m">
                <Text size="text-s">
                  <Text
                    size="text-s"
                    weight="600"
                    color="sand-12"
                    family="monospace"
                    as="span"
                  >
                    1.
                  </Text>{' '}
                  Run the following{' '}
                  <Tooltip asChild content="View installation instructions">
                    <Text
                      size="text-s"
                      href="https://github.com/nearai/nearai#nearai"
                      target="_blank"
                    >
                      NEAR AI CLI
                    </Text>
                  </Tooltip>{' '}
                  command to download this {entry.category} locally:
                </Text>

                <Card background="sand-2" padding="s">
                  <Code
                    bleed
                    language="shell"
                    source={`nearai registry download ${idForEntry(entry)}`}
                    showLineNumbers={false}
                  />
                </Card>
              </Flex>

              <Flex direction="column" gap="m">
                <Text size="text-s">
                  <Text
                    size="text-s"
                    weight="600"
                    color="sand-12"
                    family="monospace"
                    as="span"
                  >
                    2.
                  </Text>{' '}
                  Navigate to the downloaded source code and make changes:
                </Text>

                <Card background="sand-2" padding="s">
                  <Code
                    bleed
                    language="shell"
                    source={`cd ~/.nearai/registry/${idForEntry(entry)}`}
                    showLineNumbers={false}
                  />
                </Card>
              </Flex>

              <Flex direction="column" gap="m">
                <Text size="text-s">
                  <Text
                    size="text-s"
                    weight="600"
                    color="sand-12"
                    family="monospace"
                    as="span"
                  >
                    3.
                  </Text>{' '}
                  Publish your changes:
                </Text>

                <Card background="sand-2" padding="s">
                  <Code
                    bleed
                    language="shell"
                    source={`nearai registry upload .`}
                    showLineNumbers={false}
                  />
                </Card>
              </Flex>
            </Flex>
          </Dialog.Content>
        </Dialog.Root>
      )}
    </>
  );
};
