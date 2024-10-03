import {
  CodeBlock,
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
  type useCurrentEntryEnvironmentVariables,
} from '~/hooks/entries';
import { type entryModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { api } from '~/trpc/react';
import { copyTextToClipboard } from '~/utils/clipboard';
import { handleClientError } from '~/utils/error';

import { Button } from './lib/Button';
import { Card, CardList } from './lib/Card';
import { Dialog } from './lib/Dialog';
import { Flex } from './lib/Flex';
import { Form } from './lib/Form';
import { Input } from './lib/Input';
import { InputTextarea } from './lib/InputTextarea';
import { Sidebar } from './lib/Sidebar';
import { SvgIcon } from './lib/SvgIcon';
import { Text } from './lib/Text';
import { Tooltip } from './lib/Tooltip';
import { SignInPrompt } from './SignInPrompt';

type Props = {
  entry: z.infer<typeof entryModel>;
  variables: ReturnType<typeof useCurrentEntryEnvironmentVariables>;
};

export const EntryEnvironmentVariables = ({
  entry,
  variables: { variables },
}: Props) => {
  const [selectedVariable, setSelectedVariable] =
    useState<EntryEnvironmentVariable | null>(null);
  const [secretModalIsOpen, setSecretModalIsOpen] = useState(false);

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
                  <Tooltip content="Copy key to clipboard">
                    <Text
                      size="text-s"
                      weight={500}
                      color="sand-12"
                      forceWordBreak
                      onClick={() => copyTextToClipboard(variable.key)}
                    >
                      {variable.key}
                    </Text>
                  </Tooltip>

                  <Tooltip asChild content="Configure Secret">
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
                      style={{
                        position: 'relative',
                        top: '0.15rem',
                        marginLeft: 'auto',
                      }}
                    />
                  </Tooltip>
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

                    <Tooltip content="Copy value to clipboard">
                      <Text
                        size="text-xs"
                        family="monospace"
                        forceWordBreak
                        onClick={() =>
                          copyTextToClipboard(variable?.metadataValue ?? '')
                        }
                        style={{
                          textDecoration:
                            variable.urlValue ?? variable.secret
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

                    <Tooltip content="Copy value to clipboard">
                      <Text
                        size="text-xs"
                        family="monospace"
                        forceWordBreak
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

                    <Tooltip content="Copy value to clipboard">
                      <Text
                        size="text-xs"
                        family="monospace"
                        forceWordBreak
                        onClick={() =>
                          copyTextToClipboard(variable.secret?.value ?? '')
                        }
                      >
                        {variable.secret.value}
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
  const addMutation = api.hub.addSecret.useMutation();
  const removeMutation = api.hub.removeSecret.useMutation();
  const utils = api.useUtils();
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);

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
      if (existingVariable?.secret) {
        await removeMutation.mutateAsync({
          category: entry.category,
          key: existingVariable.key,
          name: entry.name,
          namespace: entry.namespace,
          version: entry.version,
        });
      }

      await addMutation.mutateAsync({
        category: entry.category,
        key: data.key,
        name: entry.name,
        namespace: entry.namespace,
        value: data.value,
        version: entry.version,
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
        category: entry.category,
        key: existingVariable.key,
        name: entry.name,
        namespace: entry.namespace,
        version: entry.version,
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
        {isAuthenticated ? (
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
