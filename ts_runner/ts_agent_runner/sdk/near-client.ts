import {AgentRunnerConfig} from './config-manager.js';
import {OpenAI, toFile} from "openai";

type FileObject = OpenAI.Files.FileObject;
type ChatCompletionMessageParam = OpenAI.ChatCompletionMessageParam;
type ChatCompletionCreateParams = OpenAI.ChatCompletionCreateParams;
type ChatCompletion = OpenAI.ChatCompletion
type Message = OpenAI.Beta.Threads.Messages.Message;
type MessageCreateParams = OpenAI.Beta.Threads.Messages.MessageCreateParams;
type ChatCompletionTool = OpenAI.ChatCompletionTool;

function getPrivateHubClient(user_auth: string, base_url: string): OpenAI {
    return new OpenAI({baseURL: base_url, apiKey: user_auth});
}

export class NearAIClient {
    private hub_client: OpenAI;
    private thread_id;
    private env_vars;

    constructor(config: AgentRunnerConfig) {
        this.hub_client = getPrivateHubClient(config.user_auth, config.base_url);
        this.thread_id = config.thread_id;
        this.env_vars = config.env_vars;
    }

    list_files_from_thread = async (order: "asc" | "desc" | undefined = "asc",
                                    thread_id: string | undefined = undefined): Promise<Array<FileObject>> => {

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

    env_var = (key: string): string | undefined => {
        return this.env_vars?.[key];
    }

    write_file = async (filename: string, content: string, encoding: string = "utf-8", filetype: string = "text/plain"): Promise<FileObject> => {
        return this.hub_client.files.create({
            file: await toFile(Buffer.from(content), filename),
            purpose: 'assistants'
        });

    }

    read_file_by_id = async (file_id: string): Promise<string> => {
        let content = await this.hub_client.files.content(file_id);
        // TODO error handling
        return await content.text();
    };


    private _listMessages = async (limit: number | undefined = undefined, order: "asc" | "desc" | undefined = "asc", thread_id: string | undefined = undefined): Promise<Array<Message>> => {
        let messages = await this.hub_client.beta.threads.messages.list(thread_id || this.thread_id, {
            order: order
        }, {});
        return messages.data;
    };


    completions = async (messages: Array<ChatCompletionMessageParam>, model: string = "",
                         max_tokens: number = 4000,
                         temperature: number = 0.7,
                         tools?: Array<ChatCompletionTool>,
                         stream: boolean = false): Promise<ChatCompletion> => {
        return await this._run_inference_completions(messages, model, stream, temperature, max_tokens, tools);
    };


    private _run_inference_completions = async (
        messages: Array<ChatCompletionMessageParam>, model: string, stream: boolean, temperature: number, max_tokens: number,
        tools?: Array<ChatCompletionTool>): Promise<ChatCompletion> => {
        const params: ChatCompletionCreateParams =
            {
                model: model,
                messages: messages,
                // stream: stream,
                temperature: temperature,
                max_tokens: max_tokens,
                tools: tools
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
    list_messages = async (thread_id: string | undefined = undefined, limit: number | undefined = undefined,
                           order: "asc" | "desc" | undefined = "asc"): Promise<Message[]> => {
        let messages = await this._listMessages(limit, order, thread_id);
        return messages;
    }

    get_thread_id = (): string => {
        return this.thread_id;
    }
}
