"use client";

import { useEffect, useState } from "react";
import { type z } from "zod";
import { Button } from "~/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from "~/components/ui/form";
import { Textarea } from "~/components/ui/textarea";
import { useZodForm } from "~/hooks/form";
import { parseHashParams, stringToUint8Array } from "~/hooks/misc";
import {
  CALLBACK_URL,
  CONVERSATION_PATH, CURRENT_AUTH, NONCE, PLAIN_MSG, RECIPIENT,
  useSendCompletionsRequest,
} from "~/hooks/mutations";
import { useListModels } from "~/hooks/queries";
import {authorizationModel, chatCompletionsModel, type messageModel} from "~/lib/models";
import { Conversation } from "./bubble";
import { NearLogin } from "./near";

import { DropDownForm } from "./role";
import { SliderFormField } from "./slider";

const roles = [
  { label: "User", value: "user" },
  { label: "Assistant", value: "assistant" },
  { label: "System", value: "system" },
];

const providers = [
  { label: "Fireworks", value: "fireworks" },
  { label: "Hyperbolic", value: "hyperbolic" },
];

const useLocalStorage = (key) => {
  const [storedValue, setStoredValue] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(key);
    }
    return null;
  });

  useEffect(() => {
    const handleStorageChange = () => {
      if (typeof window !== 'undefined') {
        setStoredValue(localStorage.getItem(key));
      }
    };

    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [key]);

  const setValue = (value) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(key, value);
      setStoredValue(value);
    }
  };

  return [storedValue, setValue];
};

export function Chat() {
  const form = useZodForm(chatCompletionsModel);
  const chat = useSendCompletionsRequest();
  const listModels = useListModels(form.watch("provider"));
  const [conversation, setConversation] = useState<
    z.infer<typeof messageModel>[]
  >([]);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [accountId, setAccountId] = useState("");
  const [authValue, setAuthValue] = useLocalStorage(CURRENT_AUTH);

  async function onSubmit(values: z.infer<typeof chatCompletionsModel>) {
    values.messages = [...conversation, ...values.messages];
    console.log("values", values);

    values.messages.map((m) => console.log(m.content));

    const resp = await chat.mutateAsync(values);
    const respMsg = resp.choices[0]!.message;

    let storedConversation = localStorage.getItem(CONVERSATION_PATH);
    if (storedConversation) {
      try {
        let storedConversationData = JSON.parse(storedConversation);
        storedConversationData.messages = [...storedConversationData?.messages ?? [], respMsg];
        console.log("Storing in localStorage the conversation", storedConversationData);
        localStorage.setItem(CONVERSATION_PATH, JSON.stringify(storedConversationData));
      } catch (error) {
        throw new Error('Failed to parse Conversation JSON: ' + error.message);
      }
    }

    setConversation(() => [...values.messages, respMsg]);
  }

  function clearConversation() {
    localStorage.removeItem(CONVERSATION_PATH);
    setConversation([]);
  }

  useEffect(() => {
      if (authValue) {
          setIsAuthenticated(true);
          if (authValue.startsWith('Bearer ')) {
            try {
              const authJson = JSON.parse(authValue.substring(7));
              setAccountId(authJson.account_id);
            } catch (error) {
              throw new Error('Failed to parse Auth JSON: ' + error.message);
            }
          }
      } else {
          setIsAuthenticated(false);
      }
  }, [authValue]);

  useEffect(() => {
    const hashParams = parseHashParams(location.hash);
    if (hashParams.signature) {
      const auth = authorizationModel.parse({
        account_id: hashParams.accountId,
        public_key: hashParams.publicKey,
        signature: hashParams.signature,
        callback_url: CALLBACK_URL,
        plainMsg: PLAIN_MSG,
        recipient: RECIPIENT,
        nonce: [...stringToUint8Array(NONCE)]
      });
      setAuthValue(`Bearer ${JSON.stringify(auth)}`)

      // cleanup url
      window.history.replaceState(null, '', window.location.pathname + window.location.search);
    }
  }, []);

  useEffect(() => {
    const currConv = localStorage.getItem(CONVERSATION_PATH);
    if (currConv) {
      const conv: unknown = JSON.parse(currConv);
      const parsed = chatCompletionsModel.parse(conv);
      setConversation(parsed.messages);
    }
  }, [setConversation]);

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <div className="flex flex-row">
          <div className="flex w-[20%] flex-col justify-between p-4">
            <div>History</div>
            {isAuthenticated &&
              <Button type="button" onClick={clearConversation}>
                Clear Conversation
              </Button>
            }
          </div>

          <div className="flex h-screen w-[80%] flex-col justify-between bg-gray-100">
            <div className="flex-grow overflow-y-auto p-6">
              {!isAuthenticated ? <div className={"pt-6 text-center"}>Login with NEAR to continue</div> : <Conversation messages={conversation} /> }
            </div>
            <div className="space-y-2 bg-white p-4">
              <FormField
                control={form.control}
                name="messages.0.content"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Textarea
                        readOnly={!isAuthenticated}
                        placeholder="Type your message..."
                        className="w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {isAuthenticated ?
                <Button
                  type="submit"
                  className="w-full"
                  disabled={chat.isPending === true}
                >
                  Send as {accountId}
                </Button> : <NearLogin /> }
              {isAuthenticated && JSON.stringify(form.formState.errors) !== "{}" && (
                <div className="text-red-500">
                  {JSON.stringify(form.formState.errors)}
                </div>
              )}
            </div>
          </div>
          <div className="flex w-[20%] flex-col justify-between space-y-2 p-4">
            <div className="flex flex-col gap-3">
              <span>Parameters</span>
              <hr />
              <DropDownForm
                title="Provider"
                name="provider"
                defaultValue={"fireworks"}
                choices={providers}
              />
              <DropDownForm
                title="Model"
                name="model"
                defaultValue={
                  "fireworks::accounts/fireworks/models/mixtral-8x22b-instruct"
                }
                choices={listModels.data ?? []}
              />
              <DropDownForm
                title="Role"
                name="messages.0.role"
                defaultValue={"user"}
                choices={roles}
              />
              <SliderFormField
                control={form.control}
                name="temperature"
                description="The temperature for sampling"
                max={2}
                min={0}
                step={0.01}
                defaultValue={0.1}
              />
              <SliderFormField
                control={form.control}
                name="max_tokens"
                description="The maximum number of tokens to generate"
                max={2048}
                min={1}
                step={1}
                defaultValue={128}
              />
            </div>
            <div>
              { isAuthenticated && <Button
                      onClick={() => {
                        localStorage.removeItem(CURRENT_AUTH);
                        setIsAuthenticated(false);
                      }}
                      type="button"
                  >
                    Sign Out
                  </Button>
               }
            </div>
          </div>
        </div>
      </form>
    </Form>
  );
}
