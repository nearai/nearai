'use client';

import {
  Badge,
  Button,
  Card,
  Container,
  Flex,
  PlaceholderStack,
  Section,
  SvgIcon,
  Text,
} from '@nearai/ui';
import {
  Archive,
  Check,
  DownloadSimple,
  FilePlus,
  Info,
  Warning,
} from '@phosphor-icons/react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { type z } from 'zod';

import { useCurrentEntry, useCurrentEntryParams } from '@/hooks/entries';
import { type entryModel } from '@/lib/models';
import { trpc } from '@/trpc/TRPCProvider';
import {
  downloadBlob,
  exportAgentAsTar,
  type ExportProgress,
} from '@/utils/export';

export default function ExportGuidePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState<ExportProgress>({
    current: 0,
    total: 0,
  });
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportSuccess, setExportSuccess] = useState(false);

  // Get agent ID from URL params or search params
  const agentId = searchParams.get('agent');
  const urlParams = useCurrentEntryParams();

  // Parse agent ID if provided
  const agentParams = agentId
    ? (() => {
        const parts = agentId.split('/');
        return {
          namespace: parts[0] || '',
          name: parts[1] || '',
          version: parts[2] || 'latest',
        };
      })()
    : urlParams.namespace && urlParams.name
      ? urlParams
      : null;

  // Fetch current agent if params are available
  const { currentEntry } = useCurrentEntry('agent', {
    enabled: !!agentParams,
    overrides: agentParams || undefined,
  });

  // Fetch file paths for the agent
  const filePathsQuery = trpc.hub.filePaths.useQuery(
    {
      namespace: agentParams?.namespace || '',
      name: agentParams?.name || '',
      version: agentParams?.version || 'latest',
      category: 'agent',
    },
    {
      enabled: !!agentParams && !!currentEntry,
    },
  );

  const handleExport = async (entry: z.infer<typeof entryModel>) => {
    if (!filePathsQuery.data) return;

    setIsExporting(true);
    setExportError(null);
    setExportSuccess(false);

    try {
      const tarBlob = await exportAgentAsTar(
        entry,
        filePathsQuery.data,
        setExportProgress,
      );

      const filename =
        `${entry.namespace}-${entry.name}-${entry.version}.tar`.replace(
          /[^a-zA-Z0-9-_.]/g,
          '_',
        );

      downloadBlob(tarBlob, filename);
      setExportSuccess(true);
    } catch (error) {
      console.error('Export failed:', error);
      setExportError(error instanceof Error ? error.message : 'Export failed');
    } finally {
      setIsExporting(false);
    }
  };

  // Auto-redirect to agents page if no agent is selected
  useEffect(() => {
    if (!agentParams && !urlParams.namespace) {
      const timer = setTimeout(() => {
        router.push('/agents');
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [agentParams, urlParams.namespace, router]);

  if (!agentParams) {
    return (
      <Section grow="available">
        <Container size="s">
          <Card padding="l" background="amber-1">
            <Flex direction="column" gap="l" align="center">
              <SvgIcon icon={<Info />} size="xl" color="amber-11" />
              <Text size="text-xl" weight={600}>
                No Agent Selected
              </Text>
              <Text color="sand-11">
                Please navigate to an agent page and click the Export button, or
                you will be redirected to the agents page...
              </Text>
              <Button
                label="Browse Agents"
                href="/agents"
                variant="primary"
                icon={<Archive />}
              />
            </Flex>
          </Card>
        </Container>
      </Section>
    );
  }

  if (!currentEntry) {
    return (
      <Section grow="available">
        <Container size="s">
          <PlaceholderStack />
        </Container>
      </Section>
    );
  }

  return (
    <Section grow="available">
      <Container size="m">
        <Flex direction="column" gap="xl">
          {/* Header */}
          <Flex direction="column" gap="m">
            <Text size="text-3xl" weight={700}>
              Export Agent
            </Text>
            <Text size="text-l" color="sand-11">
              Download all files for your agent as a tar archive
            </Text>
          </Flex>

          {/* Agent Info Card */}
          <Card padding="l" background="sand-2">
            <Flex direction="column" gap="m">
              <Flex align="center" gap="m" wrap="wrap">
                <Text size="text-l" weight={600}>
                  {currentEntry.name}
                </Text>
                <Badge label={`v${currentEntry.version}`} variant="neutral" />
                <Text size="text-s" color="sand-11">
                  by {currentEntry.namespace}
                </Text>
              </Flex>

              {currentEntry.description && (
                <Text color="sand-11">{currentEntry.description}</Text>
              )}

              <Flex align="center" gap="s" wrap="wrap">
                <SvgIcon icon={<FilePlus />} size="s" color="sand-10" />
                <Text size="text-s" color="sand-10">
                  {filePathsQuery.data?.length || 0} files to export
                </Text>
              </Flex>
            </Flex>
          </Card>

          {/* Export Button and Status */}
          <Card padding="l">
            <Flex direction="column" gap="l">
              {exportError && (
                <Card padding="m" background="red-2">
                  <Flex align="center" gap="s">
                    <SvgIcon icon={<Warning />} color="red-11" />
                    <Text color="red-11" size="text-s">
                      {exportError}
                    </Text>
                  </Flex>
                </Card>
              )}

              {exportSuccess && (
                <Card padding="m" background="green-2">
                  <Flex align="center" gap="s">
                    <SvgIcon icon={<Check />} color="green-11" />
                    <Text color="green-11" size="text-s">
                      Export completed successfully!
                    </Text>
                  </Flex>
                </Card>
              )}

              {isExporting && (
                <Card padding="m" background="amber-2">
                  <Flex direction="column" gap="s">
                    <Flex align="center" gap="s">
                      <Text size="text-s">
                        Exporting files... {exportProgress.current}/
                        {exportProgress.total}
                      </Text>
                    </Flex>
                    {exportProgress.currentFile && (
                      <Text size="text-xs" color="sand-11">
                        Current file: {exportProgress.currentFile}
                      </Text>
                    )}
                  </Flex>
                </Card>
              )}

              <Flex gap="m" wrap="wrap">
                <Button
                  label={
                    isExporting ? 'Exporting...' : 'Download as TAR Archive'
                  }
                  icon={<DownloadSimple />}
                  variant="primary"
                  onClick={() => handleExport(currentEntry)}
                  disabled={isExporting || !filePathsQuery.data}
                  size="large"
                />

                <Button
                  label="View Source"
                  variant="secondary"
                  href={`/agents/${currentEntry.namespace}/${currentEntry.name}/${currentEntry.version}/source`}
                />
              </Flex>
            </Flex>
          </Card>

          {/* Instructions */}
          <Card padding="l" background="sand-1">
            <Flex direction="column" gap="m">
              <Text size="text-l" weight={600}>
                Export Instructions
              </Text>

              <Flex direction="column" gap="s">
                <Text>1. Click the "Download as TAR Archive" button above</Text>
                <Text>
                  2. The agent files will be packaged into a .tar archive
                </Text>
                <Text>3. Save the file to your desired location</Text>
                <Text>4. Extract the archive using your preferred tool:</Text>
                <Card padding="s" background="sand-3">
                  <Text family="monospace" size="text-s">
                    tar -xvf {currentEntry.namespace}-{currentEntry.name}-
                    {currentEntry.version}.tar
                  </Text>
                </Card>
                <Text>
                  5. The extracted folder will contain all agent files and a
                  README with metadata
                </Text>
              </Flex>
            </Flex>
          </Card>

          {/* Warning about wind-down */}
          <Card padding="l" background="amber-1">
            <Flex align="start" gap="m">
              <SvgIcon icon={<Warning />} color="amber-11" size="l" />
              <Flex direction="column" gap="s">
                <Text weight={600} color="amber-12">
                  Important: Export Your Agents
                </Text>
                <Text size="text-s" color="amber-11">
                  As NEAR AI transitions to focus on DCML, please ensure you
                  export all your important agents before the shutdown date.
                  This export contains all necessary files to preserve and
                  potentially migrate your agent elsewhere.
                </Text>
              </Flex>
            </Flex>
          </Card>
        </Flex>
      </Container>
    </Section>
  );
}

