"use client";
import {Three} from "~/components/ui/typography";
import {useHandleLogin} from "~/hooks/login";
import {useZodForm} from "~/hooks/form";
import {agentRequestModel, type messageModel} from "~/lib/models";
import {AGENT_CONVERSATION_PATH, useSendAgentRequest} from "~/hooks/mutations";
import {useState} from "react";
import usePersistingStore from "~/store/store";
import {Form, FormControl, FormField, FormItem, FormMessage} from "~/components/ui/form";
import {Conversation} from "~/app/_components/bubble";
import {Textarea} from "~/components/ui/textarea";
import {Button} from "~/components/ui/button";
import {NearLogin} from "~/app/_components/near";
import {DropDownForm} from "~/app/_components/role";
import {SliderFormField} from "~/app/_components/slider";
import {api} from "~/trpc/react";
import HydrationZustand from "~/app/_components/hydration";
import { z } from "zod";
import SimpleTabs from "~/components/ui/tabs";

interface Environment {
    environmentName: string,
    fileStructure: object,
    files: object;
}

function Chat() {
    useHandleLogin();

    const form = useZodForm(agentRequestModel);
    const chat = useSendAgentRequest();
    const listAgents = api.hub.listRegistry.useQuery({ category: "agent" });
    const [conversation, setConversation] = useState<
      z.infer<typeof messageModel>[]
    >([]);
    const [fileStructure, setFileStructure] = useState<object>({});
    const [files, setFiles] = useState<object>({});
    const [previousEnvironmentName, setPreviousEnvironmentName] = useState<string>("");

    const store = usePersistingStore();

    async function onSubmit(values: z.infer<typeof agentRequestModel>) {
        if(previousEnvironmentName) {
            values.environment_id = previousEnvironmentName;
        }

        const response = await chat.mutateAsync(values);
        if(response) {
            setPreviousEnvironmentName(() => response.environmentName);
            const parsedChat = response.chat;
            setConversation(parsedChat);
            setFileStructure(response.fileStructure);
            setFiles(response.files);
        }
    }

    function clearConversation() {
        localStorage.removeItem(AGENT_CONVERSATION_PATH);
        setConversation([]);
        setPreviousEnvironmentName("");
        setFileStructure({});
        setFiles({});
    }

    // useEffect(() => {
    //     const currConv = localStorage.getItem(AGENT_CONVERSATION_PATH);
    //     if (currConv) {
    //         const conv: unknown = JSON.parse(currConv);
    //         const parsed = agentRequestModel.parse(conv);
    //         setConversation(parsed.messages);
    //     }
    // }, [setConversation]);

    function listUniqueAgents(data) {
        const values =  data?.map((d) =>
          ({label: `${d.namespace} ${d.name} ${d.version}`, value: `${d.namespace}/${d.name}/${d.version}`}))
          ?? [];
        return values.sort((a, b) => (a.value > b.value) - (a.value < b.value))
          .filter((value, index, array) => {
            return (index === 0) || (value.value !== array[index-1].value);
        })
    }

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)}>
                <div className="flex flex-row">
                    <div className="flex w-[100%] flex-col">
                        <Three>Agent chat</Three>
                    </div>
                </div>
                <div className="flex flex-row gap-2">
                    <div className="flex w-[40%] flex-col justify-between bg-gray-100" >
                        <div>{previousEnvironmentName ? `Previous environment: ${previousEnvironmentName}` : ""}</div>
                        <div className="p-6" >
                            {!store.isAuthenticated() ? (
                                <div className={"pt-6 text-center"}>
                                    Login with NEAR to continue
                                </div>
                            ) : (
                              <div className="overflow-y-scroll align-items-start max-h-[50vh]">
                                <Conversation messages={conversation} />
                              </div>
                            )}
                        </div>
                        <div className="space-y-2 bg-white p-4">
                            <FormField
                                control={form.control}
                                name="new_message"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormControl>
                                            <Textarea
                                                readOnly={!store.isAuthenticated()}
                                                placeholder="Type your message..."
                                                className="w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                                                {...field}
                                                onKeyDown={(e) => {
                                                  if (e.key === "Enter" && !e.shiftKey) {
                                                    e.preventDefault();
                                                    form.handleSubmit(onSubmit)();
                                                  }
                                                }
                                              }
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            {store.isAuthenticated() ? (
                                <Button
                                    type="submit"
                                    className="w-full p-4"
                                    disabled={chat.isPending === true}
                                >
                                    Send as {store.auth?.account_id}
                                </Button>
                            ) : (
                                <NearLogin />
                            )}
                            {store.isAuthenticated() &&
                                JSON.stringify(form.formState.errors) !== "{}" && (
                                    <div className="text-red-500">
                                        {JSON.stringify(form.formState.errors)}
                                    </div>
                                )}
                        </div>
                    </div>
                    <div className="flex w-[40%] flex-col justify-between bg-gray-100">
                        <div style={{marginBottom: "auto"}}>
                        {fileStructure && Object.keys(fileStructure).length > 0 && (
                          <SimpleTabs tabs={fileStructure} content={files}/>
                        )}
                        {!fileStructure || Object.keys(fileStructure).length === 0 && (
                          <div>Files:</div>
                        )}
                        </div>
                    </div>
                    <div className="flex w-[20%] flex-col justify-between space-y-2 p-4">
                        <div className="flex flex-col gap-3">
                            <span>Parameters</span>
                            <hr />
                            <DropDownForm
                                title="Agent"
                                name="agent_id"
                                defaultValue={
                                    "flatirons.near/xela-agent/5"
                                }
                                choices={listUniqueAgents(listAgents.data)}
                            />
                            <SliderFormField
                                control={form.control}
                                name="max_iterations"
                                description="The maximum number iterations to run the agent for."
                                max={20}
                                min={1}
                                step={1}
                                defaultValue={5}
                            />
                        </div>

                        <div className="flex flex-col gap-2">
                            {store.isAuthenticated() && (
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={clearConversation}
                                >
                                    Clear Conversation
                                </Button>
                            )}
                        </div>
                    </div>
                </div>
            </form>
        </Form>
    );
}


export default function Page() {

    return (
        <div className="flex flex-col gap-2 px-24 py-4">
            <HydrationZustand>
                <Chat />
            </HydrationZustand>
        </div>
    );
}


