import {configManager} from './config-manager.js';
import type {SecureHubClient} from './secure-client.js';
import {AgentEnvironment} from "./agent-environment.js";

class GlobalEnvironment {
    private static instance: GlobalEnvironment | null = null;
    private _client: SecureHubClient | null = null;
    private _initialized = false;

    public thread_id: string = "";

    private constructor() {
        console.log("GlobalEnvironment const");
    }

    static getInstance(): GlobalEnvironment {
        console.log("GlobalEnvironment getInstance", GlobalEnvironment.instance)
        if (!GlobalEnvironment.instance) {
            GlobalEnvironment.instance = new GlobalEnvironment();
        }
        return GlobalEnvironment.instance;
    }

    initialize(jsonString: string, agentPath: string) {
        console.log("initialize GlobalENVб ", jsonString, this._initialized)
        if (this._initialized) return;

        configManager.initialize(jsonString);
        this._client = configManager.getSecureClient();
        this._initialized = true;

        this.thread_id = configManager.thread_id;

        console.log("initialized GlobalENV", this._client, this._initialized)

        const agentEnv = new AgentEnvironment();
        agentEnv.runAgent(agentPath).catch(err => console.error('Fatal error:', err));
    }

    get client(): SecureHubClient {
        // console.log("get GLOBALENV client", this._client)
        if (!this._client) {
            throw new Error('Global Environment not initialized. Call initialize() first.');
        }
        return this._client;
    }
}

export const globalEnv = GlobalEnvironment.getInstance();

console.log("globalEnv in globalEnv", globalEnv)