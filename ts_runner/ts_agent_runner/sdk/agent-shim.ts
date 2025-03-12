import OpenAI from 'openai';
import {VectorStore} from "openai/resources/beta";
import {
    FileChunkingStrategyParam,
    VectorStoreCreateParams
} from "openai/src/resources/beta/vector-stores/vector-stores";
import {FilePurpose} from "openai/src/resources/files";

import {globalEnv} from './global-env.js';

type Message = OpenAI.Beta.Threads.Messages.Message;
type FileObject = OpenAI.Files.FileObject;
type ChatCompletionMessageParam = OpenAI.ChatCompletionMessageParam;
type ChatCompletionTool = OpenAI.ChatCompletionTool;

class Environment {
    async write_file(filename: string, content: string, encoding: string = "utf-8", filetype: string = "text/plain",
                     write_to_disk: boolean = true): Promise<FileObject> {
        return await globalEnv.client.write_file(filename, content, encoding, filetype);
    }

    async read_file(filename: string): Promise<string> {
        return new Promise(async (resolve, reject) => {
            if (globalEnv.client && "list_files_from_thread" in globalEnv.client && "read_file_by_id" in globalEnv.client) {

                let threadFiles = await globalEnv.client.list_files_from_thread();

                let fileContent = "";
                for (const f of threadFiles) {
                    if (f.filename === filename) {
                        fileContent = await globalEnv.client.read_file_by_id(f.id);
                        break;
                    }
                }

                resolve(fileContent.toString());
            } else {
                reject("Client not initialized");
            }
        });

    }

    async completion(messages: Array<ChatCompletionMessageParam>, model: string = "",
                     max_tokens: number = 4000,
                     temperature: number = 0.7,
                     tools?: Array<ChatCompletionTool>,
    ): Promise<string | null> {
        if (globalEnv.client && "completions" in globalEnv.client) {
            let raw_response = await globalEnv.client.completions(messages, model, max_tokens, temperature, tools);
            // TODO error handling
            let response = raw_response as OpenAI.ChatCompletion;
            let choices = response.choices;
            let response_message = choices[0].message.content;
            return response_message
        } else {
            return null
        }
    }

    async add_reply(message: string | null, message_type: string = ""): Promise<Message> {
        return globalEnv.client.add_reply(message || "", message_type);
    }

    env_var(key: string): string | undefined {
        return globalEnv.client.env_var(key);
    }

    async list_messages(thread_id: string | undefined = undefined, limit: number | undefined = undefined,
                        order: "asc" | "desc" | undefined = "asc"):
        Promise<Array<Message>> {
        return globalEnv.client.list_messages(thread_id, limit, order);
    }

    async get_last_message(role: string = "user"): Promise<Message | null> {
        let messages = await this.list_messages();
        for (let message of messages.reverse()) {
            if (message.role === role) {
                return message;
            }
        }
        return null;
    }

    async get_last_message_content(role: string = "user"): Promise<string> {
        let message = await this.get_last_message(role);
        if (message && message.content?.[0]?.type == "text") {
            return message.content[0].text.value
        } else {
            return "";
        }
    }

    async query_vector_store(vector_store_id: string, query: string, full_files: boolean = false): Promise<any> {
        return globalEnv.client.query_vector_store(vector_store_id, query, full_files)
    }

    async add_file_to_vector_store(vector_store_id: string, file_id: string): Promise<any> {
        return globalEnv.client.add_file_to_vector_store(vector_store_id, file_id)
    }

    async create_vector_store(
        name: string,
        file_ids: string[],
        expires_after: VectorStoreCreateParams.ExpiresAfter,
        chunking_strategy: FileChunkingStrategyParam,
        metadata: unknown | null = null
    ): Promise<VectorStore | null> {
        return globalEnv.client.create_vector_store(name, file_ids, expires_after, chunking_strategy, metadata)
    }

    async upload_file(file_content: string, purpose: FilePurpose, encoding: string = "utf-8", file_name: string = "file.txt",
                      file_type: string = "text/plain"): Promise<FileObject> {
        return globalEnv.client.upload_file(file_content, purpose, encoding, file_name, file_type);
    }


    get_thread_id(): string {
        return globalEnv.client.get_thread_id()
    }
}

export const env = new Environment();