import OpenAI from "openai";

type FileObject = OpenAI.Files.FileObject;
type ChatCompletionMessageParam = OpenAI.ChatCompletionMessageParam;
type ChatCompletion = OpenAI.ChatCompletion
type Message = OpenAI.Beta.Threads.Messages.Message;
type ChatCompletionTool = OpenAI.ChatCompletionTool;

export interface SecureHubClient {
    env_var(key: string): string | undefined;

    list_files_from_thread(order?: string, thread_id?: string | undefined): Promise<Array<FileObject>>;

    completions(messages: Array<ChatCompletionMessageParam>, model?: string,
                max_tokens?: number,
                temperature?: number,
                tools?: Array<ChatCompletionTool>): Promise<ChatCompletion>;

    read_file_by_id(file_id: string): Promise<string>;

    add_reply(message: string, message_type: string | undefined): Promise<Message>;

    list_messages(thread_id: string | undefined, limit: number | undefined, order: "asc" | "desc" | undefined): Promise<Array<Message>>

    write_file(filename: string, content: string, encoding: string, filetype: string): Promise<FileObject>

    get_thread_id(): string;
}