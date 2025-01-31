import {AgentRunnerConfig} from './config-manager.js';
import OpenAI from "openai";
import {SecureHubClient} from "./secure-client.js";
import {AgentConfig} from "./config-types.js";
import {globalEnv} from "./global-env.js";

type FileObject = OpenAI.Files.FileObject;
type ChatCompletionMessageParam = OpenAI.ChatCompletionMessageParam;
type ChatCompletionCreateParams = OpenAI.ChatCompletionCreateParams;
type ChatCompletion = OpenAI.ChatCompletion
type Message = OpenAI.Beta.Threads.Messages.Message;
type MessageCreateParams = OpenAI.Beta.Threads.Messages.MessageCreateParams;

function getPrivateHubClient(user_auth: string) {
    const api_url = "https://api.near.ai"
    // const api_url = "http://127.0.0.1:8081"
    // const api_url = "http://host.docker.internal:8081"

    // const auth = {
    //     "account_id": "zavodil.near",
    //     "signature": "NgcIvBpS7nUig0GsTQZ9Ti9XjJYNsQZNwAIs4iIq9yZDlMdhZpoS1V7S2Z6H7rBpp7X3mugsTTV/YvGN+VeBBQ==",
    //     "public_key": "ed25519:HFd5upW3ppKKqwmNNbm56JW7VHXzEoDpwFKuetXLuNSq",
    //     "callback_url": "http://localhost:53382/capture",
    //     "nonce": "1733346982804",
    //     "recipient": "ai.near",
    //     "message": "Welcome to NEAR AI",
    //     "on_behalf_of": null
    // };

    // const signature = JSON.stringify(auth);
    const baseUrl = api_url + "/v1";
    console.log("agentConfig.user_auth", user_auth)
    return new OpenAI({baseURL: baseUrl, apiKey: user_auth});
}

//
// export function createNearAIClient(): SecureHubClient {
//     const client = new NearAIClient(agentConfig);
//
//     return {
//         completions(messages: Array<ChatCompletionMessageParam>, model: string = "") {
//             return client.completions(messages, model);
//         }, list_files_from_thread(order?: string, thread_id?: string | undefined): Promise<Array<FileObject>> {
//             return client.list_files_from_thread(order, thread_id);
//         }, read_file_by_id(file_id: string): Promise<string> {
//             return client.read_file_by_id(file_id);
//         }
//     };
// }


export class NearAIClient {
    private hub_client;
    private thread_id;

    constructor(config: AgentRunnerConfig) {
        this.hub_client = getPrivateHubClient(config.user_auth);
        this.thread_id = config.thread_id;
    }


    // private hub_client = getPrivateHubClient();
    // private _thread_id = "thread_57feb9f2041f4449ac5d135c";

    list_files_from_thread = async (order: string = "asc", thread_id: string | undefined = undefined): Promise<Array<FileObject>> => {

        let messages = await this._listMessages(undefined, order, thread_id);
        let attachments = messages.flatMap(m => m.attachments ?? []);
        let file_ids = attachments.map(a => a.file_id) || [];

        let files = await Promise.all(
            file_ids.map(async (fileId) => {
                if (!fileId) return null; // Проверяем, что fileId существует
                return await this.hub_client.files.retrieve(fileId);
            })
        );

        return files.filter((f): f is FileObject => f !== null); // Убираем null-значения


    };

    read_file_by_id = async (file_id: string): Promise<string> => {
        let content = await this.hub_client.files.content(file_id);
        // TODO error handling
        return await content.text();
    };


    private _listMessages = async (limit: number | undefined = undefined, order: string = "asc", thread_id: string | undefined = undefined): Promise<Array<Message>> => {
        let messages = await this.hub_client.beta.threads.messages.list(thread_id || this.thread_id);
        // console.log("_listMessages", messages)
        // TODO error handling
        return messages.data;
    };


    completions = async (messages: Array<ChatCompletionMessageParam>, model: string = "", stream: boolean = false): Promise<ChatCompletion> => {
        return await this._run_inference_completions(messages, model, stream, 1, 4000);
    };


    private _run_inference_completions = async (messages: Array<ChatCompletionMessageParam>, model: string, stream: boolean, temperature: number, max_tokens: number): Promise<ChatCompletion> => {
        const params: ChatCompletionCreateParams =
            {
                model: model,
                messages: messages,
                // stream: stream,
                temperature: temperature,
                max_tokens: max_tokens
            };

        return this.hub_client.chat.completions.create(params);
    }

    add_reply = async (message: string, message_type: string = ""): Promise<Message> => {
        let body: MessageCreateParams = {
            role: "assistant",
            content: message,
            metadata: message_type ? {message_type: message_type} : undefined
        };

        return this.hub_client.beta.threads.messages.create(
            this.thread_id,
            body
        );
    }


    /*
        def list_messages(
        self,
        thread_id: Optional[str] = None,
        limit: Union[int, NotGiven] = NOT_GIVEN,  # api defaults to 20
        order: Literal["asc", "desc"] = "asc",
    ):
        """Backwards compatibility for chat_completions messages."""
        messages = self._list_messages(thread_id=thread_id, limit=limit, order=order)

        # Filter out system and agent log messages when running in debug mode. Agent behavior shouldn't change based on logs.  # noqa: E501
        messages = [
            m
            for m in messages
            if not (m.metadata and m.metadata["message_type"] in ["system:log", "agent:log"])  # type: ignore
        ]
        legacy_messages = [
            {
                "id": m.id,
                "content": "\n".join([c.text.value for c in m.content]),  # type: ignore
                "role": m.role,
            }
            for m in messages
        ]
        return legacy_messages
     */

    list_messages = async (thread_id: string | undefined = undefined, limit: number | undefined = undefined, order: string = "asc"): Promise<Array<Message>> => {
        let messages = await this._listMessages(limit, order, thread_id);
        return messages;
    }


}

export function createSecureClient(config: AgentConfig): SecureHubClient {
    const client = new NearAIClient(config);

    return {
        completions(messages: Array<ChatCompletionMessageParam>, model: string = "") {
            return client.completions(messages, model);
        },
        list_files_from_thread(order?: string, thread_id?: string | undefined) {
            return client.list_files_from_thread(order, thread_id);
        },
        read_file_by_id(file_id: string) {
            return client.read_file_by_id(file_id);
        },
        add_reply(message: string, message_type?: string): Promise<Message> {
            return client.add_reply(message, message_type);
        },
        list_messages(thread_id: string | undefined = undefined, limit: number | undefined = undefined, order: string = "asc"): Promise<Array<Message>> {
            //list_messages(thread_id?: string | undefined, limit?: number | undefined, order?: string): Promise<Array<Message>>  {
            return client.list_messages(thread_id, limit, order);
        }
    };
}
