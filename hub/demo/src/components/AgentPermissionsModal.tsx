import { Check, Prohibit } from '@phosphor-icons/react';
import Link from 'next/link';
import { useEffect } from 'react';
import { type z } from 'zod';

import { useEntryParams } from '~/hooks/entries';
import { idForEntry } from '~/lib/entries';
import {
  type agentWalletTransactionRequestModel,
  type chatWithAgentModel,
  type entryModel,
} from '~/lib/models';
import { useAgentSettingsStore } from '~/stores/agent-settings';
import { useAuthStore } from '~/stores/auth';

import { Button } from './lib/Button';
import { Dialog } from './lib/Dialog';
import { Flex } from './lib/Flex';
import { SvgIcon } from './lib/SvgIcon';
import { Text } from './lib/Text';
import { SignInPrompt } from './SignInPrompt';

export type AgentRequest =
  | z.infer<typeof chatWithAgentModel>
  | z.infer<typeof agentWalletTransactionRequestModel>;

type Props = {
  agent: z.infer<typeof entryModel>;
  requests: AgentRequest[] | null;
  clearRequests: () => unknown;
  onAllow: (requests: AgentRequest[]) => unknown;
};

export function checkAgentPermissions(
  agent: z.infer<typeof entryModel>,
  requests: AgentRequest[],
) {
  const settings = useAgentSettingsStore.getState().getAgentSettings(agent);
  let allowRemoteRunCallsToOtherAgents = true;
  let allowWalletTransactionRequests = true;

  requests.forEach((request) => {
    if ('agent_id' in request) {
      allowRemoteRunCallsToOtherAgents =
        request.agent_id === idForEntry(agent) ||
        !!settings.allowRemoteRunCallsToOtherAgents;
    } else {
      allowWalletTransactionRequests =
        !!settings.allowWalletTransactionRequests;
    }
  });

  const allowed =
    allowRemoteRunCallsToOtherAgents && allowWalletTransactionRequests;

  return {
    allowed,
    permissions: {
      allowRemoteRunCallsToOtherAgents,
      allowWalletTransactionRequests,
    },
  };
}

export const AgentPermissionsModal = ({
  agent,
  requests,
  clearRequests,
  onAllow,
}: Props) => {
  const auth = useAuthStore((store) => store.auth);
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const { id: agentId } = useEntryParams();
  const setAgentSettings = useAgentSettingsStore(
    (store) => store.setAgentSettings,
  );
  const check = requests ? checkAgentPermissions(agent, requests) : undefined;
  const otherAgentId = requests?.find(
    (request) => 'agent_id' in request,
  )?.agent_id;

  const decline = () => {
    clearRequests();
  };

  const allow = () => {
    if (!requests) return;
    clearRequests();
    onAllow(requests);
  };

  const alwaysAllow = () => {
    if (!requests) return;

    if (!check?.permissions.allowRemoteRunCallsToOtherAgents) {
      setAgentSettings(agent, {
        allowRemoteRunCallsToOtherAgents: true,
      });
    }

    if (!check?.permissions.allowWalletTransactionRequests) {
      setAgentSettings(agent, {
        allowWalletTransactionRequests: true,
      });
    }

    clearRequests();
    onAllow(requests);
  };

  useEffect(() => {
    /*
      This logic handles the edge case of closing the modal automatically 
      if the passed request is already permitted.
    */

    if (check?.allowed) {
      clearRequests();
      requests && onAllow(requests);
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Dialog.Root open={requests !== null} onOpenChange={() => clearRequests()}>
      <Dialog.Content title="Agent Run Request" size="s">
        {isAuthenticated ? (
          <>
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
                    <Link href={`/agents/${otherAgentId}`} target="_blank">
                      <Text as="span" color="violet-11" weight={500}>
                        {otherAgentId}
                      </Text>
                    </Link>{' '}
                    using your {`account's`} signature{' '}
                    <Text as="span" color="sand-12" weight={500}>
                      {auth?.account_id}
                    </Text>
                  </Text>

                  <Flex direction="column" gap="m">
                    <Flex align="baseline" gap="s">
                      <SvgIcon
                        size="xs"
                        icon={<Check weight="bold" />}
                        color="green-10"
                      />
                      <Text size="text-s">
                        Allow the agent to execute actions within the Near AI
                        Hub.
                      </Text>
                    </Flex>

                    <Flex align="baseline" gap="s">
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

              {!check?.permissions.allowWalletTransactionRequests && (
                <>
                  <Text>
                    The current agent{' '}
                    <Link href={`/agents/${agentId}`} target="_blank">
                      <Text as="span" color="violet-11" weight={500}>
                        {agentId}
                      </Text>
                    </Link>{' '}
                    wants to request a wallet transaction. If allowed, you will
                    be prompted to review the transaction within your connected
                    wallet.
                  </Text>

                  <Flex direction="column" gap="m">
                    <Flex align="baseline" gap="s">
                      <SvgIcon
                        size="xs"
                        icon={<Check weight="bold" />}
                        color="green-10"
                      />
                      <Text size="text-s">
                        Allow the agent to request wallet transactions. You will
                        review each request within your connected wallet before
                        deciding to approve or deny it.
                      </Text>
                    </Flex>

                    <Flex align="baseline" gap="s">
                      <SvgIcon
                        size="xs"
                        icon={<Prohibit weight="bold" />}
                        color="red-10"
                      />
                      <Text size="text-s">
                        Will NOT allow the agent to perform wallet transactions
                        on your behalf without your consent.
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
          </>
        ) : (
          <>
            <SignInPrompt />
          </>
        )}
      </Dialog.Content>
    </Dialog.Root>
  );
};
