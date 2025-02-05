// import {env} from "../sdk/agent-shim.js";
import { env } from 'ts-agent-runner';
import { CdpAgentkit } from "@coinbase/cdp-agentkit-core";
import { Coinbase, Wallet } from "@coinbase/coinbase-sdk";
import { CdpToolkit } from "@coinbase/cdp-langchain";
const apiKeyName = env.env_var("CDP_API_KEY_NAME") || "";
const privateKey = (env.env_var("CDP_API_KEY_PRIVATE_KEY") ?? "").replaceAll("\\n", "\n");
const config = {
    cdpWalletData: undefined,
    networkId: env.env_var("NETWORK_ID") || "base-sepolia",
};
(async () => {
    try {
        if (apiKeyName && privateKey) {
            // Coinbase Wallet
            Coinbase.configure({
                apiKeyName,
                privateKey,
                useServerSigner: false
            });
            let wallet = await Wallet.create({ networkId: Coinbase.networks.BaseSepolia });
            console.log(`Address: ${wallet}`);
            let address = await wallet.getDefaultAddress();
            console.log(`Address: ${address}`);
            // CdpAgentkit
            const agentkit = await CdpAgentkit.configureWithWallet(config);
            const cdpWalletData = await agentkit.exportWallet();
            console.log('Agentkit initialized', cdpWalletData);
            const toolkit = new CdpToolkit(agentkit);
            let tools = toolkit.getTools();
            let tool_names = tools.map(tool => tool.name).join(", ");
            console.log('Tools available', tool_names);
            if (env.get_thread_id() !== "thead_local") {
                await env.add_reply(`Coinbase Wallet created: \`\`\` \n${wallet}\n \`\`\`\nAgentkit initialized: \`\`\` \n${cdpWalletData}\n \`\`\` \nTools available: \`\`\` \n${tool_names} \n\`\`\``);
            }
        }
        else {
            console.log("Environment variables CDP_API_KEY_NAME and CDP_API_KEY_PRIVATE_KEY not set");
        }
        let user_message = await env.get_last_message_content();
        const messages = [
            {
                "role": "assistant", "content": "Be creative and do something interesting on the blockchain. " +
                    "Choose an action or set of actions and execute it that highlights your abilities."
            },
            {
                "role": "user",
                "content": user_message
            }
        ];
        // inference
        const reply = await env.completion(messages, "llama-v3p1-70b-instruct", 4000, 0.5);
        if (env.get_thread_id() !== "thead_local") {
            await env.add_reply(reply);
        }
        console.log('Agent output:', reply);
    }
    catch (error) {
        console.error('Agent error:', error);
    }
})();
