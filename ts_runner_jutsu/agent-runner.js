import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { runner, Agent } from '@jutsuai/nearai-ts-core';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

(async () => {
    try {
        // Read the build file
        const buildInfoPath = '/var/task/build-info.txt';
        if (fs.existsSync(buildInfoPath)) {
            const buildId = fs.readFileSync(buildInfoPath, 'utf-8').trim();
            console.log(`BUILD ID: ${buildId}`);
        }

        // Call nearai-ts runner(),
        //    which reads CLI arguments to find agent path, config, etc.
        const { agentConfig, agentModule } = await runner();

        console.log('Agent environment initialized successfully.');
        console.log('Using agent config:', agentConfig);

        // Construct the Agent instance
        const agent = new Agent(agentConfig);

        // If agent code has a default export that you want to call right away:
        if (agentModule && typeof agentModule.default === 'function') {
            console.log('Calling agent’s default export...');
            const result = await agentModule.default(agent, agentConfig);
            console.log('Agent default export returned:', result);
        } else {
            console.log('No default export found in agent module (or not a function).');
        }

        console.log('All done. Exiting agent-runner.js normally.');
    } catch (err) {
        console.error('Error in agent-runner.js:', err);
        process.exit(1);
    }
})();
