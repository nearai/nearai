import OpenAI from 'openai';
// import type {ChatCompletionCreateParams} from "openai/resources";
// import {Message} from 'openai/src/resources/beta/threads/messages';
type Message = OpenAI.Beta.Threads.Messages.Message;
type FileObject = OpenAI.Files.FileObject;
type ChatCompletionMessageParam = OpenAI.ChatCompletionMessageParam;
type ChatCompletionCreateParams = OpenAI.ChatCompletionCreateParams;
type ChatCompletion = OpenAI.ChatCompletion

// import getPrivateHubClient
//import {NearAIClient} from "../sdk/agent-environment.js";
// import {nearClient as nearai} from "../sdk/agent-environment.js";

// import {configManager} from './config-manager.js';
// import type {SecureHubClient} from './secure-client.js';

// import {initializedClient} from './agent-environment.js';

import {globalEnv} from './global-env.js';

// Get the properly initialized client
// const nearai = configManager.getSecureClient();

// type Message = OpenAI.ChatCompletionMessageParam;


console.log("globalEnv shim client", globalEnv)


// const privateHub = privateHub()

// const nearai = createNearAIClient();

class Environment {
    // private _nearClient: SecureHubClient | null = null;
    //
    //
    // private get client(): SecureHubClient {
    //     if (!this._nearClient) {
    //         this._nearClient = configManager.getSecureClient();
    //     }
    //     return this._nearClient;
    // }

    async read_file(filename: string): Promise<string> {
        return new Promise(async (resolve, reject) => {
            // if (!this._nearClient) {
            //     this._nearClient = configManager.getSecureClient();
            // }

            if (globalEnv.client && "list_files_from_thread" in globalEnv.client && "read_file_by_id" in globalEnv.client) {

                let threadFiles = await globalEnv.client.list_files_from_thread();

                console.log("threadFiles", threadFiles)

                let fileContent = "";
                for (const f of threadFiles) {
                    if (f.filename === filename) {
                        fileContent = await globalEnv.client.read_file_by_id(f.id);
                        break;
                    }
                }

                console.log("threadFiles", threadFiles);
                resolve(fileContent.toString());
                //
                //
                // let file_id = "file_14b60e38589d4778b14b5e5c";
                // let content = await this._nearClient.read_file_by_id(file_id);
                // resolve(content);

            } else {
                reject("Client not initialized");
            }
            // Implementation would go here
            // resolve('File content placeholder');
        });

    }

    async completion(messages: Array<ChatCompletionMessageParam>, model: string = ""): Promise<string | null> {
        // if (!this._nearClient) {
        //     this._nearClient = configManager.getSecureClient();
        // }

        console.log("completion globalEnv", globalEnv.client)
        console.log("messages", messages)

        if (globalEnv.client && "completions" in globalEnv.client) {
            let raw_response = await globalEnv.client.completions(messages, model);
            // TODO error handling
            let response = raw_response as OpenAI.ChatCompletion;
            let choices = response.choices;
            let response_message = choices[0].message.content;
            return response_message
        } else {
            return null
        }
    }

    /*
            def add_reply(
            message: str,
            attachments: Optional[Iterable[Attachment]] = None,
            message_type: Optional[str] = None,
        ):
            """Assistant adds a message to the environment."""
            # NOTE: message from `user` are not stored in the memory

            return hub_client.beta.threads.messages.create(
                thread_id=self._thread_id,
                role="assistant",
                content=message,
                extra_body={
                    "assistant_id": self._agents[0].identifier,
                    "run_id": self._run_id,
                },
                attachments=attachments,
                metadata={"message_type": message_type} if message_type else None,
            )
     */
    async add_reply(message: string | null, message_type: string = ""): Promise<Message> {
        return globalEnv.client.add_reply(message || "", message_type);
    }

    async list_messages(thread_id: string | undefined = undefined, limit: number | undefined = undefined, order: string = "asc"):
        Promise<Array<Message>> {
        return globalEnv.client.list_messages(thread_id, limit, order);
    }

    /*    def get_last_message(self, role: str = "user"):
        """Reads last message from the given role and returns it."""
        for message in reversed(self.list_messages()):
            if message.get("role") == role:
                return message

        return None*/
    async get_last_message(role: string = "user"): Promise<Message | null> {
        let messages = await this.list_messages();
        console.log("messages", messages)
        for (let message of messages.reverse()) {
            if (message.role === role) {
                return message;
            }
        }
        return null;
    }

}

export const env = new Environment();

/*
// const nearai = configManager.getSecureClient();
export const env1 = {


    read_file: (filename: string): Promise<string> => {

        return new Promise(async (resolve, reject) => {
            let threadFiles = await nearai.list_files_from_thread();

            console.log("threadFiles", threadFiles)

            let fileContent = "";
            for (const f of threadFiles) {
                if (f.filename === filename) {
                    fileContent = await nearai.read_file_by_id(f.id);
                    break;
                }
            }

            console.log("threadFiles", threadFiles);
            resolve(fileContent);


            let file_id = "file_14b60e38589d4778b14b5e5c";
            let content = await nearai.read_file_by_id(file_id);
            resolve(content);

            // Implementation would go here
            // resolve('File content placeholder');
        });
    },

    completion: async (messages: Array<ChatCompletionMessageParam>, model: string = ""): Promise<string | null> => {
        let raw_response = await nearai.completions(messages, model);
        // TODO error handling
        let response = raw_response as OpenAI.ChatCompletion;
        let choices = response.choices;
        let response_message = choices[0].message.content;
        return response_message
    },


       getRole: (senderName: string): 'system' | 'user' | 'assistant' => {
        if (senderName === "user") {
            return "user";
        }
        return "assistant";
    },

};
*/

//
// def read_file_by_id(file_id: str):
//     """Read a file from the thread."""
//     content = hub_client.files.content(file_id).content.decode("utf-8")
//     print("file content returned by api", content)
//     return content
//
// self.read_file_by_id = read_file_by_id