import {spawn} from 'child_process';
import {readFileSync, writeFileSync} from 'fs';
import {transpile} from 'typescript';
import {fileURLToPath} from 'url';
import {dirname, join} from 'path';
import OpenAI from "openai";

type Message = OpenAI.Beta.Threads.Messages.Message;
type FileObject = OpenAI.Files.FileObject;
type ChatCompletionMessageParam = OpenAI.ChatCompletionMessageParam;
type ChatCompletionCreateParams = OpenAI.ChatCompletionCreateParams;
type ChatCompletion = OpenAI.ChatCompletion

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// import {configManager} from './config-manager.js';

export class AgentEnvironment {
    async runAgent(tsPath: string) {
        const jsCode = this.transpileCode(tsPath);
        // TODO replace with agent namespace etc
        const jsPath = join(__dirname, `${Date.now()}.agent.js`);

        console.log("Run TS Agent", jsPath);

        writeFileSync(jsPath, jsCode);

        const module = await import(jsPath);

        if (module.default) {
            module.default();
        }


    }

    private transpileCode(tsPath: string): string {
        const fullPath = join(process.cwd(), tsPath);
        const tsCode = readFileSync(fullPath, 'utf-8');
        return transpile(tsCode, {
            module: 6, // ES2022
            target: 99, // ESNext
            esModuleInterop: true,
            moduleResolution: 2 // NodeNext
        });
    }
}

class AgentRunnerConfig {
    thread_id: string;
    user_auth: string;

    // init
    constructor(thread_id: string = "", user_auth: string = "{}") {
        this.thread_id = thread_id;
        this.user_auth = user_auth;
    }
}


let agentConfig: AgentRunnerConfig = new AgentRunnerConfig();

/*


// Add this at the bottom of the file
let is_args = import.meta.url.endsWith(process.argv[1]);
if (!is_args) {

    //throw new Error('No init args');
}

const agentPath = process.argv[2];
if (!agentPath) {
    // throw new Error('Missing agent path');
}


// console.log("Staring ", agentPath)

// Получаем переданный JSON из аргументов
const jsonString = process.argv[3];

if (!jsonString) {
    // throw new Error('No configuration provided');
}
let run_required = configManager.initialize(jsonString);

// export const nearClient = configManager.getNearClient();

export const initializedClient = configManager.getSecureClient();

console.log("Starting agent with params:", jsonString);

if (run_required) {
    new AgentEnvironment()
        .runAgent(agentPath)
        .catch(err => console.error('Fatal error:', err));

}
*/


//
// let params: { [key: string]: any };
//
// try {
//     // Преобразуем строку обратно в объект
//     params = JSON.parse(jsonString);
//
//     console.log("params", params.thread_id, params.user_auth)
//
//     if (params.thread_id && params.user_auth) {
//         console.log("setting agentConfig")
//         //agentConfig.thread_id = params.thread_id;
//         // agentConfig.user_auth = params.user_auth;
//
//         agentConfig = new AgentRunnerConfig(params.thread_id, params.user_auth);
//         nearClient = createNearAIClient()
//
//     } else {
//         console.error('Invalid params:', params);
//         process.exit(1);
//     }
//     console.log('Received params:', params);
// } catch (error) {
//     console.error('Error parsing JSON:', error);
//     process.exit(1);
// }
//


// class SecureHubClientWrapper {
//     private auth = {
//         "account_id": "zavodil.near",
//         "signature": "NgcIvBpS7nUig0GsTQZ9Ti9XjJYNsQZNwAIs4iIq9yZDlMdhZpoS1V7S2Z6H7rBpp7X3mugsTTV/YvGN+VeBBQ==",
//         "public_key": "ed25519:HFd5upW3ppKKqwmNNbm56JW7VHXzEoDpwFKuetXLuNSq",
//         "callback_url": "http://localhost:53382/capture",
//         "nonce": "1733346982804",
//         "recipient": "ai.near",
//         "message": "Welcome to NEAR AI",
//         "on_behalf_of": null
//     };
//
// }

interface SecureHubClient {
    list_files_from_thread(order?: string, thread_id?: string | undefined): Promise<Array<FileObject>>;

    completions(messages: Array<ChatCompletionMessageParam>, model?: string): Promise<ChatCompletion>;

    read_file_by_id(file_id: string): Promise<string>;
}

// import {createNearAIClient} from "../sdk/agent-environment.js";

// export let nearClient = createNearAIClient()

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

function getPrivateHubClient1() {
    // const api_url = "https://api.near.ai"
    // const api_url = "http://127.0.0.1:8081"
    const api_url = "http://host.docker.internal:8081"
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
    console.log("agentConfig.user_auth", agentConfig.user_auth)
    return new OpenAI({baseURL: baseUrl, apiKey: agentConfig.user_auth});
}


function getPrivateHubClient(user_auth: string): OpenAI {
    // const api_url = "https://api.near.ai"
    // const api_url = "http://127.0.0.1:8081"
    const api_url = "http://host.docker.internal:8081"
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

// export let privateHubClient = getPrivateHubClient();

class NearAIClient_ {
    private hub_client;

    constructor(config: AgentRunnerConfig) {
        this.hub_client = getPrivateHubClient(config.user_auth);
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
        let messages = await this.hub_client.beta.threads.messages.list(thread_id || agentConfig.thread_id);
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


}

