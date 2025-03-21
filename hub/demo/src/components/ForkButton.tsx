import {
  Button,
  Dialog,
  Flex,
  Form,
  Grid,
  handleClientError,
  Input,
  InputTextarea,
  openToast,
  SvgIcon,
  Text,
  Tooltip,
} from '@nearai/ui';
import { GitFork } from '@phosphor-icons/react';
import { useRouter } from 'next/navigation';
import { type CSSProperties, useEffect, useState } from 'react';
import { type SubmitHandler, useForm } from 'react-hook-form';
import { type z } from 'zod';

import { idForEntry, primaryUrlForEntry } from '@/lib/entries';
import { type entryModel } from '@/lib/models';
import { useAuthStore } from '@/stores/auth';
import { trpc } from '@/trpc/TRPCProvider';
import { validateAlphanumericCharacters } from '@/utils/inputs';
import { toTitleCase } from '@/utils/string';

import { SignInPrompt } from './SignInPrompt';

type Props = {
  entry: z.infer<typeof entryModel> | undefined;
  style?: CSSProperties;
  variant: 'simple' | 'detailed';
};

export const ForkButton = ({ entry, style, variant = 'simple' }: Props) => {
  const auth = useAuthStore((store) => store.auth);
  const isPermittedToViewSource =
    !entry?.details.private_source || auth?.accountId === entry.namespace;
  const [forkModalIsOpen, setForkModalIsOpen] = useState(false);
  const count = entry?.num_forks ?? 0;

  const fork = () => setForkModalIsOpen(true);

  if (!isPermittedToViewSource) return null;

  return (
    <>
      <Tooltip
        asChild
        content={`Create your own copy of this ${entry?.category ?? 'agent'}`}
      >
        {variant === 'simple' ? (
          <Button
            label={count.toString()}
            iconLeft={<SvgIcon size="xs" icon={<GitFork weight="duotone" />} />}
            size="small"
            variant="secondary"
            fill="ghost"
            onClick={fork}
            style={{
              ...style,
              fontVariantNumeric: 'tabular-nums',
              paddingInline: 'var(--gap-s)',
            }}
          />
        ) : (
          <Button
            label="Fork"
            iconLeft={<SvgIcon size="xs" icon={<GitFork />} />}
            count={count}
            size="small"
            fill="outline"
            onClick={fork}
            style={style}
          />
        )}
      </Tooltip>

      {entry && (
        <Dialog.Root open={forkModalIsOpen} onOpenChange={setForkModalIsOpen}>
          <Dialog.Content
            title={`Fork ${toTitleCase(entry.category)}`}
            size="m"
          >
            <ForkForm
              entry={entry}
              onFinish={() => setForkModalIsOpen(false)}
            />
          </Dialog.Content>
        </Dialog.Root>
      )}
    </>
  );
};

type ForkFormProps = {
  entry: z.infer<typeof entryModel>;
  onFinish: () => void;
};

type ForkFormSchema = {
  name: string;
  description: string;
  version: string;
};

const ForkForm = ({ entry, onFinish }: ForkFormProps) => {
  const form = useForm<ForkFormSchema>({
    mode: 'all',
  });
  const utils = trpc.useUtils();
  const auth = useAuthStore((store) => store.auth);
  const forkMutation = trpc.hub.forkEntry.useMutation();
  const router = useRouter();
  const name = form.watch('name');

  const entriesQuery = trpc.hub.entries.useQuery(
    {
      category: entry.category,
      namespace: auth?.accountId,
    },
    {
      enabled: !!auth,
    },
  );

  useEffect(() => {
    // Set default form values
    if (!form.formState.isDirty) {
      form.setValue('name', entry.name, {
        shouldValidate: true,
      });
      form.setValue('version', entry.version);
      form.setValue('description', entry.description);
    }
  }, [form, entry]);

  useEffect(() => {
    // Whenever the entries query data changes, revalidate the name field
    form.setValue('name', form.getValues('name'), {
      shouldValidate: true,
    });
  }, [form, entriesQuery.data]);

  const onSubmit: SubmitHandler<ForkFormSchema> = async (data) => {
    try {
      const result = await forkMutation.mutateAsync({
        name: entry.name,
        namespace: entry.namespace,
        version: entry.version,
        modifications: data,
      });

      await utils.hub.entries.refetch();

      const url = primaryUrlForEntry({
        ...result.entry,
        category: entry.category,
      })!;

      router.push(url);

      openToast({
        type: 'success',
        title: `${toTitleCase(entry.category)} fork published`,
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
        {auth ? (
          <>
            <Flex align="center" gap="s">
              <SvgIcon icon={<GitFork />} color="sand-9" />
              <Text href={primaryUrlForEntry(entry)} target="_blank">
                {idForEntry(entry)}
              </Text>
            </Flex>

            <Text color="sand-12">
              Forking this {entry.category} will create a published copy under
              your account. This will allow you to freely make your own changes
              without affecting the original {entry.category}.
            </Text>

            <Text size="text-s">
              Optionally customize the name, version, and description of your
              resulting fork below.
            </Text>

            <Grid
              columns="1fr 1fr 7rem"
              gap="s"
              phone={{ columns: '1fr', gap: 'm' }}
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
                        return `Conflicts with existing ${entry.category}`;
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
                label="Fork"
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
