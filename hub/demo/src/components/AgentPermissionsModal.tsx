import {
  Badge,
  Button,
  Card,
  CardList,
  copyTextToClipboard,
  Dialog,
  Flex,
  SvgIcon,
  Text,
  Tooltip,
} from '@nearai/ui';
import {
  Check,
  Eye,
  EyeSlash,
  LockKey,
  Prohibit,
  WarningDiamond,
} from '@phosphor-icons/react';
import { useEffect, useState } from 'react';
import { type z } from 'zod';

import { APP_TITLE } from '@/constants';
import { useEntryEnvironmentVariables } from '@/hooks/entries';
import { ENTRY_CATEGORY_LABELS } from '@/lib/categories';
import {
  idForEntry,
  idMatchesEntry,
  parseEntryIdWithOptionalVersion,
} from '@/lib/entries';
import {
  type agentAddSecretsRequestModel,
  type agentNearSendTransactionsRequestModel,
  type chatWithAgentModel,
  type entryModel,
} from '@/lib/models';
import { useAgentSettingsStore } from '@/stores/agent-settings';
import { useAuthStore } from '@/stores/auth';

import { type AgentChatMutationInput } from './AgentRunner';
import { Code } from './lib/Code';
import { SignInPrompt } from './SignInPrompt';

export type AgentRequestWithPermissions =
  | {
      action: 'add_secrets';
      input: z.infer<typeof agentAddSecretsRequestModel>;
    }
  | {
      action: 'initial_user_message';
      input: AgentChatMutationInput;
    }
  | {
      action: 'remote_agent_run';
      input: z.infer<typeof chatWithAgentModel>;
    }
  | {
      action: 'near_send_transactions';
      input: z.infer<typeof agentNearSendTransactionsRequestModel>;
    };

type Props = {
  agent: z.infer<typeof entryModel>;
  requests: AgentRequestWithPermissions[] | null;
  clearRequests: () => unknown;
  onAllow: (requests: AgentRequestWithPermissions[]) => unknown;
};

export function checkAgentPermissions(
  agent: z.infer<typeof entryModel>,
  requests: AgentRequestWithPermissions[],
) {
  const settings = useAgentSettingsStore.getState().getAgentSettings(agent);
  let allowAddSecrets = true;
  let allowInitialUserMessage = true;
  let allowRemoteRunCallsToOtherAgents = true;
  let allowWalletTransactionRequests = true;

  requests.forEach(({ action, input }) => {
    if (action === 'add_secrets') {
      // Always prompt a user for permission to add secrets
      allowAddSecrets = false;
    } else if (action === 'initial_user_message') {
      // Always prompt a user for permission to run initial user message
      allowInitialUserMessage = false;
    } else if (action === 'remote_agent_run') {
      allowRemoteRunCallsToOtherAgents =
        idMatchesEntry(input.agent_id, agent) ||
        !!settings.allowRemoteRunCallsToOtherAgents;
    } else if (action === 'near_send_transactions') {
      allowWalletTransactionRequests =
        !!settings.allowWalletTransactionRequests;
    }
  });

  const allowed =
    allowAddSecrets &&
    allowInitialUserMessage &&
    allowRemoteRunCallsToOtherAgents &&
    allowWalletTransactionRequests;

  return {
    allowed,
    permissions: {
      allowAddSecrets,
      allowInitialUserMessage,
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
  const agentId = idForEntry(agent);
  const setAgentSettings = useAgentSettingsStore(
    (store) => store.setAgentSettings,
  );
  const check = requests ? checkAgentPermissions(agent, requests) : undefined;
  const otherAgentId = requests?.find(
    (request) => request.action === 'remote_agent_run',
  )?.input.agent_id;

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

  const requestsThatCanBeAlwaysAllowed =
    requests?.filter(
      ({ action }) =>
        action !== 'add_secrets' && action !== 'initial_user_message',
    ) ?? [];

  const initialUserMessageRequest = requests?.find(
    (request) => request.action === 'initial_user_message',
  );

  return (
    <Dialog.Root open={requests !== null} onOpenChange={() => clearRequests()}>
      <Dialog.Content title="Agent Request" size="s">
        {check && requests && (
          <>
            {auth ? (
              <Flex direction="column" gap="l">
                {!check.permissions.allowAddSecrets && (
                  <SecretsToAdd agent={agent} requests={requests} />
                )}

                {!check.permissions.allowInitialUserMessage &&
                  initialUserMessageRequest && (
                    <>
                      <Text>
                        The current agent{' '}
                        <Text href={`/agents/${agentId}`} target="_blank">
                          {agentId}
                        </Text>{' '}
                        wants to start a new thread with an initial message on
                        your behalf:
                      </Text>

                      <Code
                        language="markdown"
                        source={initialUserMessageRequest.input.new_message}
                      />
                    </>
                  )}

                {!check.permissions.allowRemoteRunCallsToOtherAgents && (
                  <>
                    <Text>
                      The current agent{' '}
                      <Text href={`/agents/${agentId}`} target="_blank">
                        {agentId}
                      </Text>{' '}
                      wants to send an additional request to a different agent{' '}
                      <Text href={`/agents/${otherAgentId}`} target="_blank">
                        {otherAgentId}
                      </Text>{' '}
                      using your {`account's`} signature{' '}
                      <Text as="span" color="sand-12" weight={500}>
                        {auth.accountId}
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
                          Allow the agent to execute actions within the NEAR AI
                          {APP_TITLE}.
                        </Text>
                      </Flex>

                      <Flex align="baseline" gap="s">
                        <SvgIcon
                          size="xs"
                          icon={<Prohibit weight="bold" />}
                          color="red-10"
                        />
                        <Text size="text-s">
                          Will NOT allow the agent to perform actions on your
                          NEAR blockchain account.
                        </Text>
                      </Flex>
                    </Flex>
                  </>
                )}

                {!check.permissions.allowWalletTransactionRequests && (
                  <>
                    <Text>
                      The current agent{' '}
                      <Text href={`/agents/${agentId}`} target="_blank">
                        {agentId}
                      </Text>{' '}
                      wants to request a wallet transaction. If allowed, you
                      will be prompted to review the transaction within your
                      connected wallet.
                    </Text>

                    <Flex direction="column" gap="m">
                      <Flex align="baseline" gap="s">
                        <SvgIcon
                          size="xs"
                          icon={<Check weight="bold" />}
                          color="green-10"
                        />
                        <Text size="text-s">
                          Allow the agent to request wallet transactions. You
                          will review each request within your connected wallet
                          before deciding to approve or deny it.
                        </Text>
                      </Flex>

                      <Flex align="baseline" gap="s">
                        <SvgIcon
                          size="xs"
                          icon={<Prohibit weight="bold" />}
                          color="red-10"
                        />
                        <Text size="text-s">
                          Will NOT allow the agent to perform wallet
                          transactions on your behalf without your consent.
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

                  {requestsThatCanBeAlwaysAllowed.length > 0 ? (
                    <>
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
                    </>
                  ) : (
                    <Button
                      label="Allow"
                      variant="affirmative"
                      size="small"
                      onClick={allow}
                    />
                  )}
                </Flex>
              </Flex>
            ) : (
              <SignInPrompt />
            )}
          </>
        )}
      </Dialog.Content>
    </Dialog.Root>
  );
};

const SecretsToAdd = ({
  agent,
  requests,
}: {
  agent: z.infer<typeof entryModel>;
  requests: AgentRequestWithPermissions[];
}) => {
  const agentId = idForEntry(agent);
  const [revealedSecretKeys, setRevealedSecretKeys] = useState<string[]>([]);
  const { variablesByKey } = useEntryEnvironmentVariables(agent);

  const toggleRevealSecret = (key: string) => {
    const revealed = revealedSecretKeys.find((k) => k === key);
    setRevealedSecretKeys((keys) => {
      if (!revealed) {
        return [...keys, key];
      }
      return keys.filter((k) => k !== key);
    });
  };

  const secrets = (requests ?? [])
    .flatMap((request) =>
      request.action === 'add_secrets' ? request.input.secrets : null,
    )
    .filter((value) => !!value)
    .map((secret) => {
      const { name, namespace, version } = parseEntryIdWithOptionalVersion(
        secret.agentId,
      );
      const existing = variablesByKey[secret.key]?.secret;
      const normalizedAgentId = version
        ? `${namespace}/${name}/${version}`
        : `${namespace}/${name}`;

      return {
        ...secret,
        existing,
        isExternalAgent: !idMatchesEntry(normalizedAgentId, agent),
        normalizedAgentId,
      };
    });

  if (secrets.length === 0) return null;

  return (
    <>
      <Text>
        The current agent{' '}
        <Text href={`/agents/${agentId}`} target="_blank">
          {agentId}
        </Text>{' '}
        wants to save {secrets.length}
        {` secret${secrets.length === 1 ? '' : 's'}`} to your account. Secrets
        are only visible to you and the specified agent.
      </Text>

      <CardList>
        {secrets.map((secret) => (
          <Card gap="xs" padding="s" key={secret.key} background="sand-2">
            <Flex align="center" gap="m">
              <Tooltip content="Copy to clipboard">
                <Text
                  size="text-s"
                  weight={500}
                  color="sand-12"
                  forceWordBreak
                  indicateParentClickable
                  onClick={() => copyTextToClipboard(secret.key)}
                >
                  {secret.key}
                </Text>
              </Tooltip>

              <Flex
                gap="xs"
                style={{
                  position: 'relative',
                  top: '0.15rem',
                  marginLeft: 'auto',
                }}
              >
                <Tooltip
                  asChild
                  content={`${revealedSecretKeys.includes(secret.key) ? 'Hide' : 'Show'} Secret`}
                >
                  <Button
                    label="Show/Hide Secret"
                    icon={
                      revealedSecretKeys.includes(secret.key) ? (
                        <EyeSlash />
                      ) : (
                        <Eye />
                      )
                    }
                    size="x-small"
                    fill="ghost"
                    variant="primary"
                    onClick={() => {
                      toggleRevealSecret(secret.key);
                    }}
                  />
                </Tooltip>
              </Flex>
            </Flex>

            {secret.existing && (
              <Flex align="baseline" gap="s">
                <Tooltip content="Current secret value">
                  <SvgIcon
                    style={{
                      position: 'relative',
                      top: '0.15rem',
                      cursor: 'help',
                    }}
                    icon={<WarningDiamond />}
                    color="sand-10"
                    size="xs"
                  />
                </Tooltip>

                <Tooltip content="Copy to clipboard">
                  <Text
                    size="text-xs"
                    color="red-9"
                    family="monospace"
                    forceWordBreak
                    indicateParentClickable
                    onClick={() => copyTextToClipboard(secret.existing!.value)}
                  >
                    {revealedSecretKeys.includes(secret.key)
                      ? secret.existing.value
                      : '*****'}
                  </Text>
                </Tooltip>

                <Tooltip
                  content="The current secret value will be overwritten"
                  asChild
                >
                  <Badge
                    label="Overwrite"
                    size="small"
                    variant="alert"
                    style={{ cursor: 'help' }}
                  />
                </Tooltip>
              </Flex>
            )}

            <Flex align="baseline" gap="s">
              <Tooltip content="New secret value">
                <SvgIcon
                  style={{
                    position: 'relative',
                    top: '0.15rem',
                    cursor: 'help',
                  }}
                  icon={<LockKey />}
                  color="sand-10"
                  size="xs"
                />
              </Tooltip>

              <Tooltip content="Copy to clipboard">
                <Text
                  size="text-xs"
                  family="monospace"
                  forceWordBreak
                  indicateParentClickable
                  onClick={() => copyTextToClipboard(secret.value)}
                >
                  {revealedSecretKeys.includes(secret.key)
                    ? secret.value
                    : '*****'}
                </Text>
              </Tooltip>
            </Flex>

            <Flex align="baseline" gap="s">
              <Tooltip content="Agent scope where this secret will be saved">
                <SvgIcon
                  style={{
                    position: 'relative',
                    top: '0.15rem',
                    cursor: 'help',
                  }}
                  icon={ENTRY_CATEGORY_LABELS.agent.icon}
                  color="sand-10"
                  size="xs"
                />
              </Tooltip>

              <Text
                size="text-xs"
                color={secret.isExternalAgent ? 'amber-11' : 'sand-11'}
                href={`/agents/${secret.normalizedAgentId}`}
                target="_blank"
                decoration="none"
                forceWordBreak
              >
                {secret.normalizedAgentId}
              </Text>

              {secret.isExternalAgent && (
                <Tooltip
                  content={`The current agent (${agentId}) wants to update a secret for a different agent (${secret.normalizedAgentId})`}
                  asChild
                >
                  <Badge
                    label="External"
                    size="small"
                    variant="warning"
                    style={{ cursor: 'help' }}
                  />
                </Tooltip>
              )}
            </Flex>
          </Card>
        ))}
      </CardList>
    </>
  );
};
