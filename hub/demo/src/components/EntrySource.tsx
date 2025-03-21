'use client';

import {
  BreakpointDisplay,
  Button,
  Card,
  CardList,
  Container,
  Flex,
  PlaceholderStack,
  Section,
  SvgIcon,
  Text,
  Tooltip,
} from '@nearai/ui';
import { Folder, LinkSimple, LockKey } from '@phosphor-icons/react';
import { useEffect, useState } from 'react';
import { type z } from 'zod';

import { Code } from '@/components/lib/Code';
import { Sidebar } from '@/components/lib/Sidebar';
import { useCurrentEntryParams } from '@/hooks/entries';
import { useQueryParams } from '@/hooks/url';
import { rawFileUrlForEntry } from '@/lib/entries';
import { type entryModel } from '@/lib/models';
import { useAuthStore } from '@/stores/auth';
import { trpc } from '@/trpc/TRPCProvider';
import { filePathIsImage, filePathToCodeLanguage } from '@/utils/file';

type Props = {
  entry: z.infer<typeof entryModel>;
};

export const EntrySource = ({ entry }: Props) => {
  const auth = useAuthStore((store) => store.auth);
  const isPermittedToViewSource =
    !entry.details.private_source || auth?.accountId === entry.namespace;
  const { createQueryPath, queryParams } = useQueryParams(['file']);
  const params = useCurrentEntryParams();

  const filePathsQuery = trpc.hub.filePaths.useQuery(
    { ...params, category: entry.category },
    {
      enabled: isPermittedToViewSource,
    },
  );
  const activeFilePath = queryParams.file || 'metadata.json';
  const activeFileIsCompressed =
    activeFilePath.endsWith('.zip') || activeFilePath.endsWith('.tar');
  const activeFileIsImage = filePathIsImage(activeFilePath);

  const fileQuery = trpc.hub.file.useQuery(
    { ...params, category: entry.category, filePath: activeFilePath },
    {
      enabled:
        !!activeFilePath && !activeFileIsCompressed && isPermittedToViewSource,
    },
  );

  const [sidebarOpenForSmallScreens, setSidebarOpenForSmallScreens] =
    useState(false);

  const openedFile =
    activeFilePath === fileQuery.data?.path ? fileQuery.data : undefined;

  useEffect(() => {
    setSidebarOpenForSmallScreens(false);
  }, [queryParams.file]);

  if (!isPermittedToViewSource) {
    return (
      <Section grow="available">
        <Container size="s" style={{ margin: 'auto', textAlign: 'center' }}>
          <Flex direction="column" gap="m" align="center">
            <SvgIcon icon={<LockKey />} size="l" color="amber-11" />
            <Text size="text-xl">Private Source Code</Text>
            <Text>
              You {`don't`} have permission to view the source code for this{' '}
              {entry.category}.
            </Text>
          </Flex>
        </Container>
      </Section>
    );
  }

  return (
    <>
      <Sidebar.Root>
        <Sidebar.Sidebar
          openForSmallScreens={sidebarOpenForSmallScreens}
          setOpenForSmallScreens={setSidebarOpenForSmallScreens}
        >
          <Text size="text-xs" weight={600} uppercase>
            Files
          </Text>

          {filePathsQuery.data ? (
            <Sidebar.SidebarContentBleed>
              <CardList>
                {filePathsQuery.data?.map((path) => (
                  <Card
                    padding="s"
                    paddingInline="m"
                    href={createQueryPath({ file: path })}
                    key={path}
                    background={path === activeFilePath ? 'sand-0' : 'sand-2'}
                  >
                    <Text
                      size="text-s"
                      color="sand-12"
                      weight={500}
                      clampLines={1}
                    >
                      {path}
                    </Text>
                  </Card>
                ))}
              </CardList>
            </Sidebar.SidebarContentBleed>
          ) : (
            <PlaceholderStack />
          )}
        </Sidebar.Sidebar>

        <Sidebar.Main>
          <Flex align="center" gap="m" style={{ marginBlock: '-3px' }}>
            <Flex align="center" gap="s" style={{ marginRight: 'auto' }}>
              <Text size="text-l">{activeFilePath}</Text>

              <Tooltip asChild content="Open Raw File">
                <Button
                  label="Raw"
                  icon={<LinkSimple />}
                  size="x-small"
                  fill="ghost"
                  href={rawFileUrlForEntry(entry, activeFilePath)}
                  target="_blank"
                />
              </Tooltip>
            </Flex>

            <BreakpointDisplay show="sidebar-small-screen">
              <Button
                label="View All Files"
                icon={<Folder />}
                size="small"
                fill="outline"
                onClick={() => setSidebarOpenForSmallScreens(true)}
              />
            </BreakpointDisplay>
          </Flex>

          {activeFileIsCompressed ? (
            <Text>This file type {`doesn't`} have a source preview.</Text>
          ) : (
            <>
              {openedFile ? (
                <>
                  {activeFileIsImage ? (
                    <div>
                      <img src={openedFile.content} alt={openedFile.path} />
                    </div>
                  ) : (
                    <Code
                      bleed
                      source={openedFile.content}
                      language={filePathToCodeLanguage(openedFile.path)}
                    />
                  )}
                </>
              ) : (
                <PlaceholderStack />
              )}
            </>
          )}
        </Sidebar.Main>
      </Sidebar.Root>
    </>
  );
};
