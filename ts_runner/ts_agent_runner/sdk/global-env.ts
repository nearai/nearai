import {configManager} from './config-manager.js';
import type {SecureHubClient} from './secure-client.js';
import {AgentEnvironment} from "./agent-environment.js";

class GlobalEnvironment {
    private static instance: GlobalEnvironment | null = null;
    private _client: SecureHubClient | null = null;
    private _initialized = false;

    public thread_id: string = "";

    private constructor() {
    }

    static getInstance(): GlobalEnvironment {
        if (!GlobalEnvironment.instance) {
            GlobalEnvironment.instance = new GlobalEnvironment();
        }
        return GlobalEnvironment.instance;
    }

    initialize(jsonString: string) {
        if (this._initialized) return;

        configManager.initialize(jsonString);
        this._client = configManager.getSecureClient();
        this._initialized = true;

        const agentEnv = new AgentEnvironment();
        agentEnv
            .runAgent(configManager.getConfig().agent_ts_files_to_transpile)
            .catch(err => console.error('Fatal error:', err));
    }

    get client(): SecureHubClient {
        if (!this._client) {
            throw new Error('Global Environment not initialized. Call initialize() first.');
        }
        return this._client;
    }
}

export const globalEnv = GlobalEnvironment.getInstance();