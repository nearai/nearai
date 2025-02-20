'use client';

import {
  BreakpointDisplay,
  Button,
  Card,
  CardList,
  Flex,
  Form,
  handleClientError,
  InputTextarea,
  openToast,
  PlaceholderSection,
  PlaceholderStack,
  Slider,
  Text,
  Tooltip,
} from '@near-pagoda/ui';
import { formatBytes } from '@near-pagoda/ui/utils';
import {
  ArrowRight,
  CodeBlock,
  Eye,
  Folder,
  Info,
  List,
} from '@phosphor-icons/react';
import { useMutation } from '@tanstack/react-query';
import {
  type KeyboardEventHandler,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Controller, type SubmitHandler, useForm } from 'react-hook-form';
import { type z } from 'zod';

import { AgentPermissionsModal } from '~/components/AgentPermissionsModal';
import { AgentWelcome } from '~/components/AgentWelcome';
import { EntryEnvironmentVariables } from '~/components/EntryEnvironmentVariables';
import { IframeWithBlob } from '~/components/lib/IframeWithBlob';
import { Sidebar } from '~/components/lib/Sidebar';
import { SignInPrompt } from '~/components/SignInPrompt';
import { ThreadMessages } from '~/components/threads/ThreadMessages';
import { ThreadsSidebar } from '~/components/threads/ThreadsSidebar';
import { env } from '~/env';
import { useAgentRequestsWithIframe } from '~/hooks/agent-iframe-requests';
import { useCurrentEntry, useEntryEnvironmentVariables } from '~/hooks/entries';
import { useQueryParams } from '~/hooks/url';
import { sourceUrlForEntry } from '~/lib/entries';
import { type chatWithAgentModel, type threadMessageModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { useThreadsStore } from '~/stores/threads';
import { trpc } from '~/trpc/TRPCProvider';

import { ThreadFileModal } from './threads/ThreadFileModal';

type RunView = 'conversation' | 'output' | undefined;

type Props = {
  namespace: string;
  name: string;
  version: string;
  showLoadingPlaceholder?: boolean;
};

type FormSchema = Pick<
  z.infer<typeof chatWithAgentModel>,
  'max_iterations' | 'new_message'
>;

export type AgentChatMutationInput = FormSchema &
  Partial<z.infer<typeof chatWithAgentModel>>;

export const AgentRunner = ({
  namespace,
  name,
  version,
  showLoadingPlaceholder,
}: Props) => {
  const { currentEntry, currentEntryId: agentId } = useCurrentEntry('agent', {
    namespace,
    name,
    version,
  });

  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const { queryParams, updateQueryPath } = useQueryParams([
    'showLogs',
    'threadId',
    'view',
    'transactionHashes',
    'transactionRequestId',
    'initialUserMessage',
    'mockedAitpMessages',
  ]);
  const entryEnvironmentVariables = useEntryEnvironmentVariables(
    currentEntry,
    Object.keys(queryParams),
  );
  const utils = trpc.useUtils();
  const threadId = queryParams.threadId ?? '';
  const showLogs = queryParams.showLogs === 'true';

  const form = useForm<FormSchema>({
    defaultValues: {
      max_iterations: 1,
    },
  });

  const [htmlOutput, setHtmlOutput] = useState('');
  const [openedFileName, setOpenedFileName] = useState<string | null>(null);
  const [parametersOpenForSmallScreens, setParametersOpenForSmallScreens] =
    useState(false);
  const [threadsOpenForSmallScreens, setThreadsOpenForSmallScreens] =
    useState(false);
  const formRef = useRef<HTMLFormElement | null>(null);

  const addOptimisticMessages = useThreadsStore(
    (store) => store.addOptimisticMessages,
  );
  const optimisticMessages = useThreadsStore(
    (store) => store.optimisticMessages,
  );
  const initialUserMessageSent = useRef(false);
  const chatMutationThreadId = useRef('');
  const chatMutationStartedAt = useRef<Date | null>(null);
  const resetThreadsStore = useThreadsStore((store) => store.reset);
  const setThread = useThreadsStore((store) => store.setThread);
  const threadsById = useThreadsStore((store) => store.threadsById);
  const setAddMessage = useThreadsStore((store) => store.setAddMessage);
  const thread = threadsById[chatMutationThreadId.current || threadId];

  const _chatMutation = trpc.hub.chatWithAgent.useMutation();
  const chatMutation = useMutation({
    mutationFn: async (data: AgentChatMutationInput) => {
      try {
        chatMutationStartedAt.current = new Date();

        const input = {
          thread_id: threadId || undefined,
          agent_id: agentId,
          agent_env_vars: entryEnvironmentVariables.metadataVariablesByKey,
          user_env_vars: entryEnvironmentVariables.urlVariablesByKey,
          ...data,
        };

        addOptimisticMessages(threadId, [input]);
        const response = await _chatMutation.mutateAsync(input);

        setThread({
          ...response.thread,
          files: [],
          messages: [response.message],
          run: response.run,
        });

        chatMutationThreadId.current = response.thread.id;
        updateQueryPath({ threadId: response.thread.id }, 'replace', false);

        void utils.hub.threads.refetch();
      } catch (error) {
        handleClientError({ error, title: 'Failed to run agent' });
      }
    },
  });

  const isRunning =
    _chatMutation.isPending ||
    thread?.run?.status === 'requires_action' ||
    thread?.run?.status === 'queued' ||
    thread?.run?.status === 'in_progress';

  const isLoading = isAuthenticated && !!threadId && !thread && !isRunning;

  const threadQuery = trpc.hub.thread.useQuery(
    {
      afterMessageId: thread?.latestMessageId,
      mockedAitpMessages: queryParams.mockedAitpMessages === 'true',
      runId: thread?.run?.id,
      threadId,
    },
    {
      enabled: isAuthenticated && !!threadId,
      refetchInterval: isRunning ? 150 : 1500,
      retry: false,
    },
  );

  const logMessages = useMemo(() => {
    const result = (thread ? Object.values(thread.messagesById) : []).filter(
      (message) => message.metadata?.message_type?.startsWith('system:'),
    );
    return result;
  }, [thread]);

  const messages = useMemo(() => {
    const result = [
      ...(thread ? Object.values(thread.messagesById) : []),
      ...optimisticMessages.map((message) => message.data),
    ].filter(
      (message) =>
        showLogs || !message.metadata?.message_type?.startsWith('system:'),
    );
    return result;
  }, [thread, optimisticMessages, showLogs]);

  const files = useMemo(() => {
    return thread ? Object.values(thread.filesByName) : [];
  }, [thread]);

  const latestAssistantMessages = useMemo(() => {
    const result: z.infer<typeof threadMessageModel>[] = [];
    for (let i = messages.length - 1; i >= 0; i--) {
      const message = messages[i]!;
      if (message.role === 'assistant') {
        result.unshift(message);
      } else {
        break;
      }
    }
    return result;
  }, [messages]);

  const {
    agentRequestsNeedingPermissions,
    setAgentRequestsNeedingPermissions,
    conditionallyProcessAgentRequests,
    iframePostMessage,
    onIframePostMessage,
  } = useAgentRequestsWithIframe(currentEntry, threadId);

  const [__view, __setView] = useState<RunView>();
  const view = (queryParams.view as RunView) ?? __view;
  const setView = useCallback(
    (value: RunView, updateUrl = false) => {
      __setView(value);

      if (updateUrl) {
        updateQueryPath(
          {
            view: value,
          },
          'replace',
          false,
        );
      }
    },
    [updateQueryPath],
  );

  const onSubmit: SubmitHandler<FormSchema> = async (data) => {
    form.setValue('new_message', '');
    await chatMutation.mutateAsync(data);
  };

  const onKeyDownContent: KeyboardEventHandler<HTMLTextAreaElement> = (
    event,
  ) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      formRef.current?.requestSubmit();
    }
  };

  const startNewThread = () => {
    updateQueryPath({ threadId: undefined });
    form.setValue('new_message', '');
    form.setFocus('new_message');
  };

  useEffect(() => {
    // This logic simply provides helpful logs for debugging in production

    if (!threadQuery.isFetching && (threadQuery.data || threadQuery.error)) {
      const now = new Date();
      const elapsedSecondsSinceRunStart = chatMutationStartedAt.current
        ? (now.getTime() - chatMutationStartedAt.current.getTime()) / 1000
        : null;

      console.log(
        `Thread polling fetch responded at: ${now.toLocaleTimeString()}`,
        {
          data: threadQuery.data,
          error: threadQuery.error,
          elapsedSecondsSinceRunStart,
        },
      );
    }
  }, [threadQuery.data, threadQuery.error, threadQuery.isFetching]);

  useEffect(() => {
    if (
      threadQuery.data?.metadata.topic &&
      thread?.metadata.topic !== threadQuery.data?.metadata.topic
    ) {
      // This will trigger once the inferred thread topic generator background task has resolved
      void utils.hub.threads.refetch();
    }

    if (threadQuery.data) {
      setThread(threadQuery.data);
    }
  }, [setThread, threadQuery.data, thread?.metadata.topic, utils]);

  useEffect(() => {
    if (threadQuery.error?.data?.code === 'FORBIDDEN') {
      openToast({
        type: 'error',
        title: 'Failed to load thread',
        description: `Your account doesn't have permission to access requested thread`,
      });
      updateQueryPath({ threadId: undefined });
    }
  }, [threadQuery.error, updateQueryPath]);

  useEffect(() => {
    const htmlFile = files.find((file) => file.filename === 'index.html');

    if (htmlFile) {
      const htmlContent = htmlFile.content.replaceAll(
        '{{%agent_id%}}',
        agentId,
      );
      setHtmlOutput(htmlContent);
      setView('output');
    } else {
      setHtmlOutput(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Screenshot</title>
  <style>
    html, body {
      margin: 0;
      padding: 0;
      height: 100%;
      width: 100%;
      background-color: #f0f0f0;
      font-family: sans-serif;
    }
    .full-frame {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100%;
      width: 100%;
    }
    .screenshot {
      max-width: 100%;
      max-height: 100%;
      border: 1px solid #ccc;
      border-radius: 8px;
      background-color: #fff;
    }
  </style>
</head>
<body>
  <div class="full-frame">
    <img src="data:image/png;base64,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le2nxkNpb3UsMF14ijWeNGwJALrgN6jk8V9f15tP8EfC02syass+qw3r3BuRJDdBSkhbdlfl4weRXPWxM6yip207f8Oy4xa3PB9Ms9Pk8d69f311YI1jczS21tezCNLibzG2Ak8bVPzMO+AO9d5bLdJ8a/Bl9LcQ393Lo0bN5Mys0kgtHyxPAwxOQTwa7KX4BeD55nmml1WSWRizu92CWJ5JJ29a2dF+FOhaJ4gsdbhutUnu7GPyoPtN15iomwoFxt6BScDtWCKKkGm3dtqFrczadML+O0a3EazwKkp3MY3KmXJ2hnH/AAI+lQJpOq2WmxWBtHSWbS00uYs8Hzou4B4wZfvYduDkZxXplFd39o1uy+5/5mfI+55/JaXkFpqNpcaMrwX1wkkcV1JDt2rGibT+9zn5AQR0NUv7DvbSVJLnT5JxJBFDK19PFndGWKMp87nG4feBPyg9c16bRSePq8riktfX/PyFKm2mrmTYrq9xoUqXksMF8/mCKWOM4UZPlsVJPOMEjP5VjXfhTUby5vNRN7bW2ozxQwk28TKjpHJvIf5tx3DK8EYHTrXX0VxGqOHg8EXsEZQXtqF8nUIxiJ+PtLq46t/DjHv7Vp6r4cur/wAG2uiR3MCSw/Zt0rxkq3kuj8DOeSmOveulooAxLvQ3m1bR72BoIRZTyzTIIz+8LxlDjB4655z0rmbnwBql0L0y6vBLLcWk1r50kTlmDyrIrN82MgLtwMD+Veg0UAclP4VvzrU+r297bJdC9W6gV4WKY8gQujfNnkDIIxg+tPvvDV5qF7fXFy2nTJd2cFs8EsDsh8t2Yn73ffx3BANdVRQByeleF9S0W8huLbUo5y9ulvcrco7EqjuyFG3Z4EhX5s5ABznOXaZ4TmsbzTg94j2WmSzy2yCMhyZd3DnOMKHYcDniuqooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAoooo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Ee2KFJu2gKbdtNzUorOSPUoV2p9nYHkmSR2P8qhge9WWW3ikt5JY9pkWSR2K56dvY0KTdtNwU27abmvXjH7Q7wx6FoMlxCZ4V1DMkQbaXUIcruwcZHGa9Vji1KIEqYGZuoklcgfTiuL8e+GfEOvf2XJpF1p0eoadeLfBbmZigABHTaflzxQpPTQFNu2h4XfSadq3w91TVX07SY5Vuols4dNt9stipY589sDcpUYBO4lsHIqvpzaVffC7xD5WiWkN1YCzP2xv3kzu8pDkMfurgAbR+JNei33ww1WfwjfJotrounW+piO5urhL+WaOSJT5ihMx5VP4u54HOKq6V8F/FVl4S1rSQ+lyvqhgImF0wVBGxYceXk5yaq5XMek/BbH/AAqPQunSb/0fJXfVwvg3RNQ8EeA7Cy1K5tEawjk81xO/lDdI7Z+6OzD8a6gx6k8gkYwAr0VJHCn6jFS5vXQlzavpsaVFZrRalI6s5gXb0CSuAfrxzQ8WpzEbzAoH/POV1z9eKHJq+mwObV9NjSorNkj1ObCv9nVQc5jkdT/Klkj1OUbG+zqueqSOG/PFDk1fQHNq+ho0VnNHqbJ5f+jhOBuEjhvzxQY9TMflD7Psxjd5j7vzxRzPt0Dnd9uho0Vm+Xqax+Uv2crjG5pH3fnilEepxx7E+zsPV5HLfnihSbtoCm3bTc0aKzkj1KFdqfZ3BOSZJHJ/lSRxalCuEMD56+ZK7flxQpN203BTbtpuXRMTdPDs4VA271ySMfp+tS1maVPNJcX0UysHglCZ8wsrfKGyMjj72PwrTog21dhTbcbvz/MKKKKs0CiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKAPMILS41vxJ4xj0hrcW7T2yTxTIwSbYkokXC4Iy+Mn+IAjvVy2s737H4X0rUNEnU29vayXN1b26t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ivPrG78Q2/hLw5cxalbtc6hcxGeSdJJNwkXOOX45zwuB0wB37i7Z006Zt2JBEx3Lxg7eooAs0V59o/izV/7K06zlFlLfXMNkYrgyMyATRucydy37puhG4sOlXIfGl3PJosQt7VX1T5A3mErEyOQ5PqrAYQ8ZYgd6AO1ooooAzNMl33+qxbSPLuRz65jQ1p1m6ZMr32qRAHMdyMn6xoa0qUSYu63vv+YUUUUygooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigDifCSwJ468YLZ7fs3mWzfIcjzSJPM59d3Udq7auJ8JRQ2/jrxhDakGDzLaTIbd+8ZZC/P+927V21RD4f8jfEtOq2m3t8W+y/peQUUUVZgFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQBU1P/AJBV3/1xf/0E1w/w7utP1rwrpViIFkit9MWzu45YhtkcLEG/3gffrXcan/yCrv8A64v/AOgmuM+Gd1p9x4e0aOxVBJDpyR3hWLYTOFi3EnHzH35zWc90tDWMU6M3yt2tr0WvX16eZ11roOkWMYjtdNtIUBZgqQqACw2sfxAwfapTpenma1m+xW/mWi7Ld/LGYlxjCnsMdqt0VoZGfDoWk26TpDplpGtwwaYLCoEhByCeOeea0KKKAKT6Ppkl1NdPp9q1xPH5cshiUtIn91jjkcDrRb6NplpGsdtp9rEiyCYKkSgBwNobp97HGeuKu0UAU5NJ06W/S/ksbZ7uPGydogXXAIGD16Ej8TVia3huAgmiSQI4dd6g7WHQj3FSUUAZ8mhaTMYvM0y0fySWj3QqdhLbiRxx83P15pW0TSnRkfTbRlYFWUwqQQc5B49z+Zq/RQBmt4e0Z7FbFtKsmtEcusJgXYGPUgY68nmrsdtBFKZY4Y0kKLGWVQCVXO1foMnA9zUtFAFSx0uw0xZFsLOC2WRtziGMLuPqcVHe6Lpmo3MVxe2FtcTQ/wCrkljDMn0J6VfooAgjsbSKRJI7aFHTeVZUAI3nc+P948n1NF5ZWuoWzW15bxXELYJjlQMpxyODU9FAFYafZhw4tYd4kEobYM7wuwN9dvy59OKbY6Vp+meb9gsbe281t0nkxhNx98VbooAr3VjaXwjF3bRTiJxJH5iBtjDowz0PvUcOlafb38t9DY28d3KMSTpEA7/U9T0FXKKAKkul2E+nrp8tlbvZqFVYGjBQAdMDoMY4qz5aeX5e0bMbduOMelOooAzE8O6LFZS2Uek2SWspBkhWBQjEdCRjHGBj0xU/9k6d5ZT7BbbCiIV8pcbUOUHTop5A7VcooAKKKKAM3TZEa+1SMD50uRu49Y0IrSrN01ozfaoqgeYtyN/H/TNMfXitKlEmOwUUUUygooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigDifCVvHZeOvGFrCSYvMtp8scnfIsjMPpmu2riPCFsth458YWiMWXzbe43N1zKJGI+gNdvUQVo2tY6MVPnquSnzbavTovy2CiiirOcKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigCpqf8AyCrv/ri//oJrjPhm+mnw9oy6eIvNGnJ9t2A58/bFu3e9dnqf/IKu/wDrg/8A6Ca4z4ZxabD4e0b+zzEZZdOSS82SbiJysW4MM/Kfbis5q7Wi/rsaxt7Ge99Ntt+v6HfUUUVoZBRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFAGbpvlfbtU248z7SN+Ov+rTGfwrSrN01YxfaoVx5huRv55/1aY/StKlEmO39f16hRRRTKCiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKAOI8H2xsfG/jC1MhlPm29xvIwcSCRtv4dP8ACu3riPB8Mlr448YQTSmaXzbeXzDk/I4kZV5/ujj+VdvUU1aNrWOnFzc6rk5c22trdF+WwUUUVZzBRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAVNT/5BV3/1xf8A9BNcZ8M7KysvD2jPaHMl3pyXFz+83YlKxbhjt9K7PU/+QVd/9cX/APQTXF/DPSrfTPD2jSwtIz6hpyXku8ghXZYsgYHT65rOau1pc1Ul7GcXJ6uOnR2fX03O/ooorQyCiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKAM3TY0W+1Rwfne5G7n0jQCtKs3TYVS+1SUE7pLkZ/CNBWlSiTFWWwUUUUygooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigDiPCEc0PjjxhFdSCW4823feDn92wkMa/gvFdvXEeDxcL448YLesGuvNtzkdPKIk8occcL+PrXb1FP4f8zpxbbqu7T2+HbZf0/O4UUUVZzBRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAVNT50q7/AOuD/wDoJrifhhpEel+H9JmWV5G1CwW8YMuNhZYvlHqK7bVP+QVd/wDXB/8A0E1xPww0x9P8P6TLJdNP9usFukUgjyVZYvkHJ4H4fSs5r3k7f8A2jO1Ccea13HS2+vfpb8T0GiiitDEKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAzNMhCX+qy5JMlyOPTEaCtOszTIit/qshckPcjC+mI0FadTFWRMVZbW3/MKKKKooKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooA4jwebhvHHjBr1Qt15tuMDp5QEnlHjjlfx9a7euI8ISTTeOPGEt1GIrjzbdNgGP3aiQRt+K8129RT+H/M6cWmqruktvh22X9PzuFFFFWcwUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFAFTU/wDkFXf/AFwf/wBBNcT8MLK7tPD+kyXd4bhbmwWe2QsT5MRWLCc9Meg4rttU/wCQVd/9cH/9BNcT8MLfUIfD+kvf3Cyxy2CvZqGz5cBWLap4GCPx+tZz+Jbm0W1QmuZLWOnV69P18j0GiiitDEKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAzNMRxf6q5fKNcjav8AdxGgNadZmmLIL/VWZsxm5Gwen7tM/rWnUx2Jjt9/5hRRRVFBRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQ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y4jDe2er09P62BOSejPWtO8ZaDpi3draRy/ZoUmmgl+0K/2jyhmQctlMer4FangfxAuueJte3WM9jcQQ2qPBOVLDiRgcqSMYYd68L8E6vc6zcWenLPr2o6hcOxvpm1d7dLaHIGUw3zEDLHd9AD1r034F3895ceK431e71S2t7xI7a4uZWcvGN4DfMeMgA4rHD5dSoVFUhuOU5yd2z2KiiivQEFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQByvxI0281f4fazYafbvcXU8G2OJMZY7l9a8d0Sw8fWj3B1PwSkw/sqWwt2is4dwym1FY7h8nqO+T1r6MpMD0FAHzLo/gDUoRpF5feD9bt9R02Te32BYdl3hy6lmLgowztyA3AHpXo/wAHdE13TLvxRe65pD6a+o3i3EcRxtGS5IXBPA3AV6ngegpcYoAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooA//9k=" alt="Screenshot" class="screenshot"/>
  </div>
</body>
</html>`);
      setView('output');
      // setHtmlOutput('');
      // setView('conversation');
    }
  }, [files, htmlOutput, agentId, setView]);

  useEffect(() => {
    if (currentEntry && isAuthenticated) {
      form.setFocus('new_message');
    }
  }, [threadId, currentEntry, isAuthenticated, form]);

  useEffect(() => {
    if (threadId !== chatMutationThreadId.current) {
      initialUserMessageSent.current = false;
      chatMutationThreadId.current = '';
      chatMutationStartedAt.current = null;
      resetThreadsStore();
    }
  }, [threadId, resetThreadsStore]);

  useEffect(() => {
    form.reset();
  }, [agentId, form]);

  useEffect(() => {
    if (currentEntry && !form.formState.isDirty) {
      const maxIterations =
        currentEntry.details.agent?.defaults?.max_iterations ?? 1;
      form.setValue('max_iterations', maxIterations);
    }
  }, [currentEntry, form]);

  useEffect(() => {
    setThreadsOpenForSmallScreens(false);
  }, [threadId]);

  useEffect(() => {
    const agentDetails = currentEntry?.details.agent;
    const initialUserMessage =
      queryParams.initialUserMessage || agentDetails?.initial_user_message;
    const maxIterations = agentDetails?.defaults?.max_iterations ?? 1;

    if (
      currentEntry &&
      initialUserMessage &&
      !threadId &&
      !initialUserMessageSent.current
    ) {
      initialUserMessageSent.current = true;
      void conditionallyProcessAgentRequests([
        {
          action: 'initial_user_message',
          input: {
            max_iterations: maxIterations,
            new_message: initialUserMessage,
          },
        },
      ]);
    }
  }, [
    queryParams,
    currentEntry,
    threadId,
    chatMutation,
    conditionallyProcessAgentRequests,
  ]);

  useEffect(() => {
    /*
      This allows child components within <AgentRunner> to add messages to the 
      current thread via Zustand:

      const addMessage = useThreadsStore((store) => store.addMessage);
    */

    setAddMessage(chatMutation.mutateAsync);

    () => {
      setAddMessage(undefined);
    };
  }, [chatMutation.mutateAsync, setAddMessage]);

  if (!currentEntry) {
    if (showLoadingPlaceholder) return <PlaceholderSection />;
    return null;
  }

  return (
    <>
      <Sidebar.Root>
        <ThreadsSidebar
          onRequestNewThread={startNewThread}
          openForSmallScreens={threadsOpenForSmallScreens}
          setOpenForSmallScreens={setThreadsOpenForSmallScreens}
        />

        <Sidebar.Main>
          {isLoading ? (
            <PlaceholderStack style={{ marginBottom: 'auto' }} />
          ) : (
            <>
              {view === 'output' ? (
                <>
                  <IframeWithBlob
                    html={htmlOutput}
                    height={currentEntry.details.agent?.html_height}
                    onPostMessage={onIframePostMessage}
                    postMessage={iframePostMessage}
                  />

                  {latestAssistantMessages.length > 0 &&
                    currentEntry.details.agent
                      ?.html_show_latest_messages_below && (
                      <ThreadMessages
                        grow={false}
                        messages={latestAssistantMessages}
                        scroll={false}
                        threadId={threadId}
                      />
                    )}
                </>
              ) : (
                <ThreadMessages
                  messages={messages}
                  threadId={threadId}
                  welcomeMessage={
                    <AgentWelcome details={currentEntry.details} />
                  }
                />
              )}
            </>
          )}

          <Sidebar.MainStickyFooter>
            <Form onSubmit={form.handleSubmit(onSubmit)} ref={formRef}>
              <Flex direction="column" gap="m">
                <InputTextarea
                  placeholder="Write your message and press enter..."
                  onKeyDown={onKeyDownContent}
                  disabled={!isAuthenticated}
                  {...form.register('new_message', {
                    required: 'Please enter a message',
                  })}
                />

                {isAuthenticated ? (
                  <Flex align="start" gap="m" justify="space-between">
                    <BreakpointDisplay
                      show="larger-than-phone"
                      style={{ marginRight: 'auto' }}
                    >
                      <Text size="text-xs">
                        <b>Shift + Enter</b> to add a new line
                      </Text>
                    </BreakpointDisplay>

                    <Flex
                      align="start"
                      gap="s"
                      style={{ paddingRight: '0.15rem' }}
                    >
                      <BreakpointDisplay show="sidebar-small-screen">
                        <Tooltip asChild content="View all threads">
                          <Button
                            label="Select Thread"
                            icon={<List />}
                            size="small"
                            variant="secondary"
                            fill="ghost"
                            onClick={() => setThreadsOpenForSmallScreens(true)}
                          />
                        </Tooltip>
                      </BreakpointDisplay>

                      <BreakpointDisplay show="sidebar-small-screen">
                        <Tooltip
                          asChild
                          content="View output files & agent settings"
                        >
                          <Button
                            label={files.length.toString()}
                            iconLeft={<Folder />}
                            size="small"
                            variant="secondary"
                            fill="ghost"
                            style={{ paddingInline: '0.5rem' }}
                            onClick={() =>
                              setParametersOpenForSmallScreens(true)
                            }
                          />
                        </Tooltip>
                      </BreakpointDisplay>

                      {htmlOutput && (
                        <Tooltip
                          asChild
                          content={
                            view === 'output'
                              ? 'View conversation'
                              : 'View rendered output'
                          }
                        >
                          <Button
                            label="Toggle View"
                            icon={
                              <Eye
                                weight={view === 'output' ? 'fill' : 'regular'}
                              />
                            }
                            size="small"
                            variant="secondary"
                            fill="ghost"
                            onClick={() =>
                              view === 'output'
                                ? setView('conversation', true)
                                : setView('output', true)
                            }
                          />
                        </Tooltip>
                      )}

                      <Tooltip
                        asChild
                        content={
                          showLogs ? 'Hide system logs' : 'Show system logs'
                        }
                      >
                        <Button
                          label={logMessages.length.toString()}
                          iconLeft={
                            <Info weight={showLogs ? 'fill' : 'regular'} />
                          }
                          size="small"
                          variant="secondary"
                          fill="ghost"
                          style={{ paddingInline: '0.5rem' }}
                          onClick={() =>
                            updateQueryPath(
                              { showLogs: showLogs ? undefined : 'true' },
                              'replace',
                              false,
                            )
                          }
                        />
                      </Tooltip>

                      {env.NEXT_PUBLIC_CONSUMER_MODE && (
                        <Tooltip asChild content="Inspect agent source">
                          <Button
                            label="Agent Source"
                            icon={<CodeBlock />}
                            size="small"
                            fill="ghost"
                            href={`https://app.near.ai${sourceUrlForEntry(currentEntry)}`}
                          />
                        </Tooltip>
                      )}
                    </Flex>

                    <Button
                      label="Send Message"
                      type="submit"
                      icon={<ArrowRight weight="bold" />}
                      size="small"
                      loading={isRunning}
                    />
                  </Flex>
                ) : (
                  <SignInPrompt />
                )}
              </Flex>
            </Form>
          </Sidebar.MainStickyFooter>
        </Sidebar.Main>

        <Sidebar.Sidebar
          openForSmallScreens={parametersOpenForSmallScreens}
          setOpenForSmallScreens={setParametersOpenForSmallScreens}
        >
          <Flex direction="column" gap="l">
            <Flex direction="column" gap="m">
              <Text size="text-xs" weight={600} uppercase>
                Output
              </Text>

              {isLoading ? (
                <PlaceholderStack />
              ) : (
                <>
                  {files.length ? (
                    <CardList>
                      {files.map((file) => (
                        <Card
                          padding="s"
                          gap="s"
                          key={file.id}
                          background="sand-2"
                          onClick={() => {
                            setOpenedFileName(file.filename);
                          }}
                        >
                          <Flex align="center" gap="s">
                            <Text
                              size="text-s"
                              color="sand-12"
                              weight={500}
                              clampLines={1}
                              style={{ marginRight: 'auto' }}
                            >
                              {file.filename}
                            </Text>

                            <Text size="text-xs">
                              {formatBytes(file.bytes)}
                            </Text>
                          </Flex>
                        </Card>
                      ))}
                    </CardList>
                  ) : (
                    <Text size="text-s" color="sand-10">
                      No files generated yet.
                    </Text>
                  )}
                </>
              )}
            </Flex>

            {!env.NEXT_PUBLIC_CONSUMER_MODE && (
              <>
                <EntryEnvironmentVariables
                  entry={currentEntry}
                  excludeQueryParamKeys={Object.keys(queryParams)}
                />

                <Flex direction="column" gap="m">
                  <Text size="text-xs" weight={600} uppercase>
                    Parameters
                  </Text>

                  <Controller
                    control={form.control}
                    name="max_iterations"
                    render={({ field }) => (
                      <Slider
                        label="Max Iterations"
                        max={20}
                        min={1}
                        step={1}
                        assistive="The maximum number of iterations to run the agent for, usually 1. Each iteration will loop back through your agent allowing it to act and reflect on LLM results."
                        {...field}
                      />
                    )}
                  />
                </Flex>
              </>
            )}
          </Flex>
        </Sidebar.Sidebar>
      </Sidebar.Root>

      <AgentPermissionsModal
        agent={currentEntry}
        onAllow={(requests) =>
          conditionallyProcessAgentRequests(requests, true)
        }
        requests={agentRequestsNeedingPermissions}
        clearRequests={() => setAgentRequestsNeedingPermissions(null)}
      />

      <ThreadFileModal
        filesByName={thread?.filesByName}
        openedFileName={openedFileName}
        setOpenedFileName={setOpenedFileName}
      />
    </>
  );
};
