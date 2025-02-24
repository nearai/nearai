export interface AgentConfig {
    thread_id: string;
    user_auth: string;
    base_url: string;
    agent_ts_files_to_transpile: string[];
    env_vars: { [key: string]: string };
}