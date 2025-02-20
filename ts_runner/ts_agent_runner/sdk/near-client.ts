import {AgentRunnerConfig} from './config-manager.js';
import {OpenAI, toFile} from "openai";
import {VectorStoreFile} from "openai/resources/beta/vector-stores";
import {VectorStore} from "openai/resources/beta";
import {
    FileChunkingStrategyParam,
    VectorStoreCreateParams
} from "openai/src/resources/beta/vector-stores/vector-stores";
import {FilePurpose} from "openai/src/resources/files";

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
    private base_url: string;

    constructor(config: AgentRunnerConfig) {
        this.base_url = config.base_url;
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
                if (!fileId) return null;
                return await this.hub_client.files.retrieve(fileId);
            })
        );

        return files.filter((f): f is FileObject => f !== null);


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

    query_vector_store = async (vector_store_id: string, query: string, full_files: boolean = false): Promise<string> => {
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.hub_client.apiKey}`,
        };

        const data = JSON.stringify({query, full_files});

        const endpoint = `${this.base_url}/vector_stores/${vector_store_id}/search`;

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers,
                body: data,
            });

            if (!response.ok) {
                throw new Error(`Error querying vector store: ${response.status} ${response.statusText}`);
            }

            return response.json();
        } catch (error: any) {
            throw new Error(`Error querying vector store: ${error.message}`);
        }
    }

    upload_file = async (file_content: string, purpose: FilePurpose, encoding: string = "utf-8", file_name: string = "file.txt",
                         file_type: string = "text/plain"): Promise<FileObject> => {

        const blob = new Blob([file_content], {type: file_type});
        const file = new File([blob], file_name, {type: file_type, lastModified: Date.now()});

        return this.hub_client.files.create({file, purpose});
    }

    add_file_to_vector_store = async (vector_store_id: string, file_id: string): Promise<VectorStoreFile> => {
        return this.hub_client.beta.vectorStores.files.create(vector_store_id, {file_id})
    }

    create_vector_store(
        name: string,
        file_ids: string[],
        expires_after: VectorStoreCreateParams.ExpiresAfter,
        chunking_strategy: FileChunkingStrategyParam,
        metadata: unknown | null = null
    ): Promise<VectorStore | null> {
        return this.hub_client.beta.vectorStores.create({
            name,
            file_ids,
            expires_after,
            chunking_strategy,
            metadata
        })
    }

    read_file_by_id = async (file_id: string): Promise<string> => {
        let content = await this.hub_client.files.content(file_id);
        return await content.text();
    };

    completions = async (messages: Array<ChatCompletionMessageParam>, model: string = "",
                         max_tokens: number = 4000,
                         temperature: number = 0.7,
                         tools?: Array<ChatCompletionTool>,
                         stream: boolean = false): Promise<ChatCompletion> => {
        return await this._run_inference_completions(messages, model, stream, temperature, max_tokens, tools);
    };

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

    private _listMessages = async (limit: number | undefined = undefined, order: "asc" | "desc" | undefined = "asc", thread_id: string | undefined = undefined): Promise<Array<Message>> => {
        let messages = await this.hub_client.beta.threads.messages.list(thread_id || this.thread_id, {
            order: order
        }, {});
        return messages.data;
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
}
