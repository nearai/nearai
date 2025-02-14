import {readFileSync, writeFileSync, existsSync} from 'fs';
import {transpile} from 'typescript';
import {fileURLToPath} from 'url';
import {dirname, join} from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export class AgentEnvironment {
    async runAgent(agent_ts_files_to_transpile: string[]) {
        let agent_main_js_path = "";

        for (let i in agent_ts_files_to_transpile) {
            let agent_ts_path = agent_ts_files_to_transpile[i];
            const agent_js_code = this.transpileCode(agent_ts_path);

            // filename only
            let agent_js_filename =
                (agent_ts_path.split('/').pop() || "")
                    .replace(/\.ts$/, ".js")

            if (agent_js_filename) {
                const agent_js_path = join(__dirname, agent_js_filename);

                writeFileSync(agent_js_path, agent_js_code);

                if (agent_js_filename == "agent.js") {
                    agent_main_js_path = agent_js_path;
                }
            }
        }

        const module = await import(agent_main_js_path);

        if (module.default) {
            module.default();
        }
    }

    private transpileCode(tsPath: string): string {
        let fullPath = tsPath;
        // if file exists
        if (!existsSync(tsPath)) {
            fullPath = join(process.cwd(), tsPath);
        }

        const tsCode = readFileSync(fullPath, 'utf-8');
        return transpile(tsCode, {
            module: 6, // ES2022
            target: 99, // ESNext
            esModuleInterop: true,
            moduleResolution: 2 // NodeNext
        });
    }
}