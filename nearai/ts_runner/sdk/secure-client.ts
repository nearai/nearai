import OpenAI from "openai";

type FileObject = OpenAI.Files.FileObject;
type ChatCompletionMessageParam = OpenAI.ChatCompletionMessageParam;
type ChatCompletionCreateParams = OpenAI.ChatCompletionCreateParams;
type ChatCompletion = OpenAI.ChatCompletion
type Message = OpenAI.Beta.Threads.Messages.Message;

export interface SecureHubClient {
    list_files_from_thread(order?: string, thread_id?: string | undefined): Promise<Array<FileObject>>;

    completions(messages: Array<ChatCompletionMessageParam>, model?: string): Promise<ChatCompletion>;

    read_file_by_id(file_id: string): Promise<string>;

    add_reply(message: string, message_type: string): Promise<Message>;

    list_messages(thread_id: string | undefined, limit: number | undefined, order: string): Promise<Array<Message>>

}