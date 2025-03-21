import {
  Button,
  Card,
  CardList,
  Checkbox,
  Dialog,
  Flex,
  Form,
  Grid,
  handleClientError,
  HR,
  Input,
  InputTextarea,
  openToast,
  SvgIcon,
  Text,
  Tooltip,
} from '@nearai/ui';
import {
  BookOpenText,
  FileTs,
  Lightning,
  Plus,
  TerminalWindow,
  Wallet,
  XLogo,
} from '@phosphor-icons/react';
import { useRouter } from 'next/navigation';
import { type ReactNode, useState } from 'react';
import { type SubmitHandler, useForm } from 'react-hook-form';

import { idForEntry, parseEntryId, primaryUrlForEntry } from '@/lib/entries';
import { useAuthStore } from '@/stores/auth';
import NearLogoIcon from '@/svgs/near-logo-icon-padding.svg';
import { trpc } from '@/trpc/TRPCProvider';
import { validateAlphanumericCharacters } from '@/utils/inputs';

import { SignInPrompt } from './SignInPrompt';

const BASIC_TEMPLATE_AGENT_ID = 'flatirons.near/example-travel-agent/latest';
const TWITTER_TEMPLATE_AGENT_ID = 'flatirons.near/near-secret-agent/latest';
const NEAR_TEMPLATE_AGENT_ID = 'zavodil.near/near-agent/latest';
const AGENT_KIT_TEMPLATE_AGENT_ID =
  'antonlomonos.near/cdp_langchain_chatbot_example_usage/latest';
const TYPESCRIPT_TEMPLATE_AGENT_ID = 'zavodil.near/cdp-agent/latest';

type Props = {
  customButton?: ReactNode;
};

export const NewAgentButton = ({ customButton }: Props) => {
  const [modalIsOpen, setModalIsOpen] = useState(false);

  return (
    <>
      <Dialog.Root open={modalIsOpen} onOpenChange={setModalIsOpen}>
        <Tooltip asChild content="Deploy a new agent">
          <Dialog.Trigger asChild>
            {customButton ?? (
              <Button
                label="New Agent"
                iconLeft={<Plus />}
                variant="affirmative"
              />
            )}
          </Dialog.Trigger>
        </Tooltip>

        <Dialog.Content title="Deploy a New Agent" size="m">
          <NewAgentForm onFinish={() => setModalIsOpen(false)} />
        </Dialog.Content>
      </Dialog.Root>
    </>
  );
};

const templates = [
  {
    agentId: NEAR_TEMPLATE_AGENT_ID,
    icon: <NearLogoIcon />,
    title: 'NEAR',
    description: 'View and send transactions on the blockchain',
  },
  {
    agentId: TWITTER_TEMPLATE_AGENT_ID,
    icon: <XLogo />,
    title: 'Twitter',
    description: 'Listen for events and publish tweets',
  },
  {
    agentId: AGENT_KIT_TEMPLATE_AGENT_ID,
    icon: <Wallet />,
    title: 'AgentKit by Coinbase',
    description: (
      <>
        Easily take actions onchain with any wallet -{' '}
        <Text
          size="text-s"
          href="https://github.com/coinbase/agentkit"
          target="_blank"
        >
          Learn More
        </Text>
      </>
    ),
  },
  {
    agentId: TYPESCRIPT_TEMPLATE_AGENT_ID,
    icon: <FileTs />,
    title: 'TypeScript',
    description: 'Code using a typed language',
  },
];

type NewAgentFormProps = {
  onFinish: () => void;
};

type NewAgentFormSchema = {
  agentId: string;
  description: string;
  name: string;
  version: string;
};

const NewAgentForm = ({ onFinish }: NewAgentFormProps) => {
  const form = useForm<NewAgentFormSchema>({
    mode: 'all',
    defaultValues: {
      version: '0.0.1',
    },
  });
  const utils = trpc.useUtils();
  const auth = useAuthStore((store) => store.auth);
  const forkMutation = trpc.hub.forkEntry.useMutation();
  const router = useRouter();
  const name = form.watch('name');

  const entriesQuery = trpc.hub.entries.useQuery(
    {
      category: 'agent',
      namespace: auth?.accountId,
    },
    {
      enabled: !!auth,
    },
  );

  const onSubmit: SubmitHandler<NewAgentFormSchema> = async (data) => {
    try {
      if (!auth) return;

      const { name, namespace, version } = parseEntryId(
        data.agentId || BASIC_TEMPLATE_AGENT_ID,
      );

      const result = await forkMutation.mutateAsync({
        name,
        namespace,
        version,
        modifications: data,
      });

      await utils.hub.entries.refetch();

      const url = primaryUrlForEntry({
        ...result.entry,
        category: 'agent',
      })!;

      router.push(url);

      openToast({
        type: 'success',
        title: 'Agent Deployed',
        description: idForEntry(result.entry),
      });

      onFinish();
    } catch (error) {
      handleClientError({ error });
    }
  };

  const findConflictingEntry = (name: string) => {
    if (form.formState.isSubmitting) return;
    const match = entriesQuery.data?.find((entry) => entry.name === name);
    return match;
  };

  return (
    <Form onSubmit={form.handleSubmit(onSubmit)}>
      <Flex direction="column" gap="l">
        <Flex align="center" gap="s">
          <SvgIcon icon={<Lightning weight="fill" />} color="amber-10" />
          <Text color="sand-12" weight={600}>
            Deploy a template with a few clicks
          </Text>
        </Flex>

        {auth ? (
          <>
            <Flex direction="column" gap="m">
              <Flex gap="s" direction="column">
                <Text size="text-xs" color="sand-12" weight={600}>
                  Tools To Include
                </Text>

                <Text size="text-s">
                  This determines the starting template for your agent. You can
                  freely integrate or remove tools at any time as you develop
                  your agent.
                </Text>
              </Flex>

              <CardList>
                {templates.map((template) => (
                  <Card
                    background="sand-2"
                    padding="s"
                    paddingInline="m"
                    as="label"
                    key={template.agentId}
                  >
                    <Flex align="center" gap="m">
                      <Checkbox
                        type="radio"
                        value={template.agentId}
                        {...form.register('agentId')}
                      />
                      <SvgIcon icon={template.icon} color="sand-12" size="m" />
                      <Flex as="span" direction="column">
                        <Text as="span" color="current" weight={600}>
                          {template.title}
                        </Text>
                        <Text size="text-s">{template.description}</Text>
                      </Flex>
                    </Flex>
                  </Card>
                ))}
              </CardList>
            </Flex>

            <Grid
              columns="1fr 1fr 7rem"
              phone={{ columns: '1fr', gap: 'm' }}
              gap="s"
            >
              <Input
                label="Namespace"
                name="namespace"
                value={auth.accountId}
                disabled
              />

              <Input
                label="Name"
                error={form.formState.errors.name?.message}
                {...form.register('name', {
                  required: 'Please enter a name',
                  validate: {
                    characters: validateAlphanumericCharacters,
                    conflict: (value) => {
                      if (findConflictingEntry(value)) {
                        return 'Conflicts with existing agent';
                      }
                      return true;
                    },
                  },
                })}
                success={
                  name?.trim() && !findConflictingEntry(name)
                    ? 'Available'
                    : undefined
                }
              />

              <Input
                label="Version"
                error={form.formState.errors.version?.message}
                {...form.register('version', {
                  required: 'Please enter a version',
                })}
              />
            </Grid>

            <InputTextarea
              label="Description"
              error={form.formState.errors.description?.message}
              {...form.register('description')}
            />

            <Flex align="center" gap="m">
              <Button
                label="Cancel"
                variant="secondary"
                fill="outline"
                onClick={onFinish}
                style={{ marginRight: 'auto' }}
              />

              <Button
                label="Deploy"
                variant="affirmative"
                type="submit"
                loading={form.formState.isSubmitting}
              />
            </Flex>
          </>
        ) : (
          <SignInPrompt layout="horizontal-justified" />
        )}

        <Flex align="center" gap="m">
          <HR />
          <Text size="text-s">OR</Text>
          <HR />
        </Flex>

        <Flex align="center" gap="s">
          <SvgIcon icon={<TerminalWindow weight="fill" />} color="cyan-9" />
          <Text color="sand-12" weight={600}>
            Deploy via CLI
          </Text>
        </Flex>

        <Flex
          align="center"
          gap="l"
          phone={{ direction: 'column', align: 'stretch' }}
        >
          <Flex direction="column" gap="m" style={{ marginRight: 'auto' }}>
            <Text>
              Develop your agent locally in your favorite IDE and deploy via the{' '}
              <Tooltip content="View installation instructions">
                <Text href="https://github.com/nearai/nearai" target="_blank">
                  NEAR AI CLI
                </Text>
              </Tooltip>
            </Text>
          </Flex>

          <Button
            label="View Docs"
            fill="outline"
            size="small"
            iconLeft={<BookOpenText />}
            href="https://docs.near.ai/agents/quickstart/"
            target="_blank"
          />
        </Flex>
      </Flex>
    </Form>
  );
};
