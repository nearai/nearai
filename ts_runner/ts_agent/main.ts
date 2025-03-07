import {globalEnv} from 'ts-agent-runner';
import path from "node:path";
import * as fs from 'fs';
import * as os from 'os';
import * as dotenv from "dotenv";

dotenv.config();

// Add this at the bottom of the file
let is_args = import.meta.url.endsWith(process.argv[1]);
if (!is_args) {
    throw new Error('No init args');
}

const agentPath = process.argv[2];
if (!agentPath) {
    throw new Error('Missing agent path');
}

let jsonString = process.argv[3];

if (!jsonString) {
    // try to read file ~/.nearai/config.json for local auth config
    const configPath = path.join(os.homedir(), '.nearai', 'config.json');

    try {
        const data = fs.readFileSync(configPath, 'utf-8');
        const authData = JSON.parse(data);

        const local_deployment_keys = ["CDP_API_KEY_NAME", "CDP_API_KEY_PRIVATE_KEY"];
        let getEnvVariables = (keys: string[]): Record<string, string> => {
            const result: Record<string, string> = {};

            keys.forEach((key) => {
                const value = process.env[key];
                if (value) {
                    result[key] = value;
                }
            });

            return result;
        }

        jsonString = JSON.stringify({
            user_auth: JSON.stringify(authData.auth),
            thread_id: "thread_local",
            base_url: "https://api.near.ai/v1",
            agent_ts_files_to_transpile: ["agents/agent.ts"],
            env_vars: getEnvVariables(local_deployment_keys)
        });

    } catch (error) {
        throw new Error(`No configuration provided. Please make sure you have a valid Near Auth in ${configPath}.`);
    }
}

globalEnv.initialize(jsonString);