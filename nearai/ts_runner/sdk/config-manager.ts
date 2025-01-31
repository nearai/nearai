console.log("config-man init")
import {AgentConfig} from './config-types.js'
import {NearAIClient} from './near-client.js';
import {createSecureClient} from './near-client.js';
import {SecureHubClient} from "./secure-client.js";

export class AgentRunnerConfig {
    thread_id: string;
    user_auth: string;

    // init
    constructor(thread_id: string = "", user_auth: string = "{}") {
        this.thread_id = thread_id;
        this.user_auth = user_auth;
    }
}


class ConfigManager {
    private static instance: ConfigManager;
    private config: AgentConfig | null = null;
    private secureClient: SecureHubClient | null = null;

    thread_id: string = "";

    private constructor() {
    }

    static getInstance(): ConfigManager {
        if (!ConfigManager.instance) {
            ConfigManager.instance = new ConfigManager();
        }
        return ConfigManager.instance;
    }

    initialize(jsonString: string): boolean {
        if (!jsonString) {
            return false;
        }
        console.log("jsonString", jsonString)
        try {
            if (this.secureClient) {
                return false
            }
            const params = JSON.parse(jsonString);
            this.config = {
                thread_id: params.thread_id,
                user_auth: params.user_auth
            };

            this.thread_id = params.thread_id;
            this.secureClient = createSecureClient(this.config);
            console.log("initialize config", this.config);
            return true;
        } catch (error) {
            throw new Error(`Failed to initialize config: ${error}`);
        }
    }

    getSecureClient(): SecureHubClient {
        if (!this.secureClient) {
            throw new Error('SecureClient not initialized. Call initialize() first.');
        }
        return this.secureClient;
    }

    getConfig(): AgentConfig {
        if (!this.config) {
            throw new Error('Config not initialized. Call initialize() first.');
        }
        return this.config;
    }
}

export const configManager = ConfigManager.getInstance();