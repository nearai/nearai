import {spawn} from 'child_process';
import {readFileSync, writeFileSync, existsSync} from 'fs';
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
    async runAgent(agent_main_ts_filename: string, agent_ts_files_to_transpile: string[]) {
        // TODO agent_main_ts_filename - remove or use

        console.log("agent_ts_files_to_transpile", agent_ts_files_to_transpile)

        let agent_main_js_path = "";

        for (let i in agent_ts_files_to_transpile) {
            let agent_ts_path = agent_ts_files_to_transpile[i];
            console.log("agent_ts_path", agent_ts_path)
            const agent_js_code = this.transpileCode(agent_ts_path);

            // filename only
            let agent_js_filename =
                (agent_ts_path.split('/').pop() || "")
                    .replace(/\.ts$/, ".js")

            if (agent_js_code) {
                console.log(`code for ${agent_js_filename} transpiled`)
            }

            if (agent_js_filename) {
                const agent_js_path = join(__dirname, agent_js_filename);
                console.log("Saved to", agent_js_path)

                writeFileSync(agent_js_path, agent_js_code);

                if (agent_js_filename == "agent.js") {
                    agent_main_js_path = agent_js_path;
                }
            }
        }

        console.log("agent_main_js_file", agent_main_js_path)

        const module = await import(agent_main_js_path);

        if (module.default) {
            module.default();
        }
    }

    private transpileCode(tsPath: string): string {
        console.log("initial tsPath", tsPath, existsSync(tsPath))
        let fullPath = tsPath;
        // if file exists
        if (!existsSync(tsPath)) {
            fullPath = join(process.cwd(), tsPath);
        }

        console.log("transpileCode", fullPath)

        const tsCode = readFileSync(fullPath, 'utf-8');
        return transpile(tsCode, {
            module: 6, // ES2022
            target: 99, // ESNext
            esModuleInterop: true,
            moduleResolution: 2 // NodeNext
        });
    }
}