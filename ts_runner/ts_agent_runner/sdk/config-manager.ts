import {AgentConfig} from './config-types.js'
import {NearAIClient} from './near-client.js';
// import {createSecureClient} from './near-client.js';
import {SecureHubClient} from "./secure-client.js";

export class AgentRunnerConfig {
    thread_id: string;
    user_auth: string;
    base_url: string;
    env_vars: { [key: string]: string };

    // init
    constructor(thread_id: string = "",
                user_auth: string = "{}",
                base_url: string = "https://api.near.ai",
                env_vars: { [key: string]: string } = {}
    ) {
        this.thread_id = thread_id;
        this.user_auth = user_auth;
        this.base_url = base_url;
        this.env_vars = env_vars;
    }
}


class ConfigManager {
    private static instance: ConfigManager;
    private config: AgentConfig | null = null;
    private secureClient: NearAIClient | null = null;

    // thread_id: string = "";

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
        
        try {
            if (this.secureClient) {
                return false
            }
            const params = JSON.parse(jsonString);
            this.config = {
                thread_id: params.thread_id,
                user_auth: params.user_auth,
                base_url: params.base_url,
                agent_ts_files_to_transpile: params.agent_ts_files_to_transpile,
                env_vars: params.env_vars
            };

            this.secureClient = new NearAIClient(this.config);
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
        let config = this.config;
        config.user_auth = "";
        return config;
    }
}

export const configManager = ConfigManager.getInstance();