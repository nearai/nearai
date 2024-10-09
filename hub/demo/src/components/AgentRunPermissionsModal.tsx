import { Check, Prohibit } from '@phosphor-icons/react';
import Link from 'next/link';
import { useEffect } from 'react';
import { type z } from 'zod';

import { useCurrentEntry, useEntryParams } from '~/hooks/entries';
import { idForEntry } from '~/lib/entries';
import { type chatWithAgentModel, type entryModel } from '~/lib/models';
import { useAgentSettingsStore } from '~/stores/agent-settings';
import { useAuthStore } from '~/stores/auth';

import { Button } from './lib/Button';
import { Dialog } from './lib/Dialog';
import { Flex } from './lib/Flex';
import { SvgIcon } from './lib/SvgIcon';
import { Text } from './lib/Text';

type Props = {
  request: z.infer<typeof chatWithAgentModel> | null;
  setRequest: (request: z.infer<typeof chatWithAgentModel> | null) => unknown;
  onAllow: (request: z.infer<typeof chatWithAgentModel>) => unknown;
};

export function checkAgentRunPermissions(
  agent: z.infer<typeof entryModel>,
  chat: z.infer<typeof chatWithAgentModel>,
) {
  const settings = useAgentSettingsStore.getState().getAgentSettings(agent);

  const allowRemoteRunCallsToOtherAgents =
    chat.agent_id === idForEntry(agent) ||
    settings.allowRemoteRunCallsToOtherAgents;

  const allowed = allowRemoteRunCallsToOtherAgents;

  return {
    allowed,
    permissions: {
      allowRemoteRunCallsToOtherAgents,
    },
  };
}

export const AgentRunPermissionsModal = ({
  request,
  setRequest,
  onAllow,
}: Props) => {
  const auth = useAuthStore((store) => store.auth);
  const { currentEntry } = useCurrentEntry('agent');
  const { id: agentId } = useEntryParams();
  const setAgentSettings = useAgentSettingsStore(
    (store) => store.setAgentSettings,
  );
  const check =
    currentEntry && request
      ? checkAgentRunPermissions(currentEntry, request)
      : undefined;

  const decline = () => {
    setRequest(null);
  };

  const allow = () => {
    if (!currentEntry || !request) return;
    setRequest(null);
    onAllow(request);
  };

  const alwaysAllow = () => {
    if (!currentEntry || !request) return;
    setAgentSettings(currentEntry, {
      allowRemoteRunCallsToOtherAgents: true,
    });
    setRequest(null);
    onAllow(request);
  };

  useEffect(() => {
    /*
      This logic handles the edge case of closing the modal automatically 
      if the passed request is already permitted.
    */

    if (check?.allowed) {
      setRequest(null);
      request && onAllow(request);
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Dialog.Root open={request !== null} onOpenChange={() => setRequest(null)}>
      <Dialog.Content title="Agent Run Request" size="s">
        <Flex direction="column" gap="l">
          {!check?.permissions.allowRemoteRunCallsToOtherAgents && (
            <>
              <Text>
                The current agent{' '}
                <Link href={`/agents/${agentId}`} target="_blank">
                  <Text as="span" color="violet-11" weight={500}>
                    {agentId}
                  </Text>
                </Link>{' '}
                wants to send an additional request to a different agent{' '}
                <Link href={`/agents/${request?.agent_id}`} target="_blank">
                  <Text as="span" color="violet-11" weight={500}>
                    {request?.agent_id}
                  </Text>
                </Link>{' '}
                using your {`account's`} signature{' '}
                <Text as="span" color="sand-12" weight={500}>
                  {auth?.account_id}
                </Text>
              </Text>

              <Flex direction="column" gap="m">
                <Flex align="center" gap="s">
                  <SvgIcon
                    size="xs"
                    icon={<Check weight="bold" />}
                    color="green-10"
                  />
                  <Text size="text-s">
                    Allow the agent to execute actions within the Near AI Hub.
                  </Text>
                </Flex>

                <Flex align="center" gap="s">
                  <SvgIcon
                    size="xs"
                    icon={<Prohibit weight="bold" />}
                    color="red-10"
                  />
                  <Text size="text-s">
                    Will NOT allow the agent to perform actions on your NEAR
                    blockchain account.
                  </Text>
                </Flex>
              </Flex>
            </>
          )}

          <Flex gap="s">
            <Button
              label="Decline"
              variant="secondary"
              style={{ marginRight: 'auto' }}
              size="small"
              onClick={decline}
            />
            <Button
              label="Allow Once"
              variant="affirmative"
              fill="outline"
              size="small"
              onClick={allow}
            />
            <Button
              label="Always Allow"
              variant="affirmative"
              size="small"
              onClick={alwaysAllow}
            />
          </Flex>
        </Flex>
      </Dialog.Content>
    </Dialog.Root>
  );
};
