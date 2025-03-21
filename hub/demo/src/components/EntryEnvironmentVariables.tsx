import {
  Button,
  Card,
  CardList,
  copyTextToClipboard,
  Dialog,
  Flex,
  Form,
  handleClientError,
  Input,
  InputTextarea,
  SvgIcon,
  Text,
  Tooltip,
} from '@nearai/ui';
import {
  CodeBlock,
  Eye,
  EyeSlash,
  LinkSimple,
  LockKey,
  Pencil,
  Plus,
  Trash,
} from '@phosphor-icons/react';
import { useEffect, useState } from 'react';
import { type SubmitHandler, useForm } from 'react-hook-form';
import { type z } from 'zod';

import {
  type EntryEnvironmentVariable,
  useCurrentEntryParams,
  useEntryEnvironmentVariables,
} from '@/hooks/entries';
import { type entryModel } from '@/lib/models';
import { useAuthStore } from '@/stores/auth';
import { trpc } from '@/trpc/TRPCProvider';

import { Sidebar } from './lib/Sidebar';
import { SignInPrompt } from './SignInPrompt';

type Props = {
  entry: z.infer<typeof entryModel>;
  excludeQueryParamKeys?: string[];
};

export const EntryEnvironmentVariables = ({
  entry,
  excludeQueryParamKeys,
}: Props) => {
  const { variables } = useEntryEnvironmentVariables(
    entry,
    excludeQueryParamKeys,
  );
  const [selectedVariable, setSelectedVariable] =
    useState<EntryEnvironmentVariable | null>(null);
  const [secretModalIsOpen, setSecretModalIsOpen] = useState(false);
  const [revealedSecretKeys, setRevealedSecretKeys] = useState<string[]>([]);

  const toggleRevealSecret = (key: string) => {
    const revealed = revealedSecretKeys.find((k) => k === key);
    setRevealedSecretKeys((keys) => {
      if (!revealed) {
        return [...keys, key];
      }
      return keys.filter((k) => k !== key);
    });
  };

  const descriptionForMetadataValue = (variable: EntryEnvironmentVariable) => {
    let description = `Value provided by ${entry.category} metadata (details.env_vars).`;
    if (variable.secret) {
      description += ` This value is currently being overridden by a secret you've configured.`;
    } else if (variable.urlValue) {
      description += ` This value is currently being overridden by a URL query parameter.`;
    }
    return description;
  };

  const descriptionForUrlValue = (variable: EntryEnvironmentVariable) => {
    let description = `Value provided by URL query parameter.`;
    if (variable.secret) {
      description += ` This value is currently being overridden by a secret you've configured.`;
    }
    return description;
  };

  return (
    <Flex direction="column" gap="m">
      <Flex align="center" gap="s">
        <Text size="text-xs" weight={600} uppercase>
          Environment Variables
        </Text>

        <Tooltip asChild content="Configure a new secret for this agent">
          <Button
            label="Configure Secret"
            icon={<Plus weight="bold" />}
            variant="affirmative"
            size="x-small"
            fill="ghost"
            onClick={() => {
              setSelectedVariable(null);
              setSecretModalIsOpen(true);
            }}
          />
        </Tooltip>
      </Flex>

      {variables.length > 0 ? (
        <Sidebar.SidebarContentBleed>
          <CardList>
            {variables.map((variable) => (
              <Card
                padding="s"
                paddingInline="m"
                gap="s"
                background="sand-2"
                key={variable.key}
              >
                <Flex align="baseline" gap="s">
                  <Tooltip content="Copy to clipboard">
                    <Text
                      size="text-s"
                      weight={500}
                      color="sand-12"
                      forceWordBreak
                      indicateParentClickable
                      onClick={() => copyTextToClipboard(variable.key)}
                    >
                      {variable.key}
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
                    {variable.secret && (
                      <Tooltip
                        asChild
                        content={`${revealedSecretKeys.includes(variable.key) ? 'Hide' : 'Show'} secret`}
                      >
                        <Button
                          label="Show/Hide Secret"
                          icon={
                            revealedSecretKeys.includes(variable.key) ? (
                              <EyeSlash />
                            ) : (
                              <Eye />
                            )
                          }
                          size="x-small"
                          fill="ghost"
                          variant="primary"
                          onClick={() => {
                            toggleRevealSecret(variable.key);
                          }}
                        />
                      </Tooltip>
                    )}

                    <Tooltip
                      asChild
                      content={
                        variable.secret ? 'Edit secret' : 'Configure as secret'
                      }
                    >
                      <Button
                        label="Configure Secret"
                        icon={<Pencil />}
                        size="x-small"
                        fill="ghost"
                        variant="primary"
                        onClick={() => {
                          setSelectedVariable(variable);
                          setSecretModalIsOpen(true);
                        }}
                      />
                    </Tooltip>
                  </Flex>
                </Flex>

                {variable.metadataValue && (
                  <Flex align="baseline" gap="s">
                    <Tooltip content={descriptionForMetadataValue(variable)}>
                      <SvgIcon
                        style={{
                          position: 'relative',
                          top: '0.15rem',
                          cursor: 'help',
                        }}
                        icon={<CodeBlock />}
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
                        onClick={() =>
                          copyTextToClipboard(variable?.metadataValue ?? '')
                        }
                        style={{
                          textDecoration:
                            (variable.urlValue ?? variable.secret)
                              ? 'line-through'
                              : undefined,
                        }}
                      >
                        {variable.metadataValue}
                      </Text>
                    </Tooltip>
                  </Flex>
                )}

                {variable.urlValue && (
                  <Flex align="baseline" gap="s">
                    <Tooltip content={descriptionForUrlValue(variable)}>
                      <SvgIcon
                        style={{
                          position: 'relative',
                          top: '0.15rem',
                          cursor: 'help',
                        }}
                        icon={<LinkSimple />}
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
                        onClick={() =>
                          copyTextToClipboard(variable?.urlValue ?? '')
                        }
                        style={{
                          textDecoration: variable.secret
                            ? 'line-through'
                            : undefined,
                        }}
                      >
                        {variable.urlValue}
                      </Text>
                    </Tooltip>
                  </Flex>
                )}

                {variable.secret && (
                  <Flex align="baseline" gap="s">
                    <Tooltip content="Value you've configured as a secret.">
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
                        onClick={() =>
                          copyTextToClipboard(variable.secret?.value ?? '')
                        }
                      >
                        {revealedSecretKeys.includes(variable.key)
                          ? variable.secret.value
                          : '*****'}
                      </Text>
                    </Tooltip>
                  </Flex>
                )}
              </Card>
            ))}
          </CardList>
        </Sidebar.SidebarContentBleed>
      ) : (
        <Text size="text-s" color="sand-10">
          No variables configured yet.
        </Text>
      )}

      <Dialog.Root open={secretModalIsOpen} onOpenChange={setSecretModalIsOpen}>
        <Dialog.Content title="Configure Secret" size="s">
          <SecretForm
            entry={entry}
            existingVariable={selectedVariable}
            onFinish={() => setSecretModalIsOpen(false)}
          />
        </Dialog.Content>
      </Dialog.Root>
    </Flex>
  );
};

type SecretFormProps = {
  entry: z.infer<typeof entryModel>;
  existingVariable: EntryEnvironmentVariable | null;
  onFinish: () => void;
};

type SecretFormSchema = {
  key: string;
  value: string;
};

const SecretForm = ({ entry, existingVariable, onFinish }: SecretFormProps) => {
  const form = useForm<SecretFormSchema>({});
  const addMutation = trpc.hub.addSecret.useMutation();
  const removeMutation = trpc.hub.removeSecret.useMutation();
  const utils = trpc.useUtils();
  const auth = useAuthStore((store) => store.auth);
  const params = useCurrentEntryParams();

  useEffect(() => {
    if (!form.formState.isDirty) {
      if (existingVariable) {
        form.setValue('key', existingVariable.key);
        form.setValue('value', existingVariable.secret?.value ?? '');
        setTimeout(() => {
          form.setFocus('value');
        });
      } else {
        setTimeout(() => {
          form.setFocus('key');
        });
      }
    }
  }, [existingVariable, form]);

  const onSubmit: SubmitHandler<SecretFormSchema> = async (data) => {
    try {
      await addMutation.mutateAsync({
        category: entry.category,
        key: data.key,
        name: entry.name,
        namespace: entry.namespace,
        value: data.value,
        version: params.version || entry.version,
      });

      await utils.hub.secrets.refetch();

      onFinish();
    } catch (error) {
      handleClientError({ error });
    }
  };

  const remove = async () => {
    try {
      if (!existingVariable?.secret) {
        return;
      }

      await removeMutation.mutateAsync({
        ...existingVariable.secret,
        category: entry.category,
      });

      await utils.hub.secrets.refetch();

      onFinish();
    } catch (error) {
      handleClientError({ error });
    }
  };

  return (
    <Form onSubmit={form.handleSubmit(onSubmit)}>
      <Flex direction="column" gap="l">
        {auth ? (
          <>
            <Flex direction="column" gap="m">
              <Text size="text-s">
                Secrets are saved to your account and are tied to this specific{' '}
                {entry.category} version. Secrets are only visible to you and
                this {entry.category}.
              </Text>

              <Text size="text-xs" color="sand-10">
                A secret will override the value of any existing metadata or URL
                query parameter variable with the same key.
              </Text>
            </Flex>

            {auth.accountId === entry.namespace && (
              <Card background="amber-2" border="amber-4">
                <Text color="amber-11" size="text-s">
                  You are the owner of this {entry.category}. Any secrets you
                  save will be inherited (but NOT visible) when other users run
                  this {entry.category}. Users of your {entry.category} can add
                  their own secrets to override these default values for
                  themselves.
                </Text>
              </Card>
            )}

            <Input
              label="Key"
              error={form.formState.errors.key?.message}
              {...form.register('key', {
                required: 'Please enter a key',
              })}
              disabled={!!existingVariable}
            />

            <InputTextarea
              label="Value"
              enterKeySubmitsForm
              error={form.formState.errors.value?.message}
              {...form.register('value', {
                required: 'Please enter a value',
              })}
            />

            <Flex align="center" gap="m">
              <Button
                label="Cancel"
                variant="secondary"
                fill="outline"
                onClick={onFinish}
                style={{ marginRight: 'auto' }}
              />
              {existingVariable?.secret && (
                <Tooltip asChild content="Delete this secret">
                  <Button
                    label="Delete"
                    variant="destructive"
                    fill="outline"
                    onClick={remove}
                    icon={<Trash />}
                    loading={
                      !form.formState.isSubmitting && removeMutation.isPending
                    }
                  />
                </Tooltip>
              )}
              <Button
                label="Save"
                variant="affirmative"
                type="submit"
                loading={form.formState.isSubmitting}
              />
            </Flex>
          </>
        ) : (
          <SignInPrompt />
        )}
      </Flex>
    </Form>
  );
};
