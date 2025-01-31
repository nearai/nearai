// Change the import to use explicit .js extension

import {env} from "../sdk/agent-shim.js";

// import {createNearAIClient} from "../sdk/agent-environment.js";

export async function run() {
    try {
        // let n = createNearAIClient()
        console.log('Agent started');


        const content = await env.read_file('output.txt');
        console.log('File output:', content);

        // raise event completionAgent
        //const eventEmitter = new EventEmitter();
        //eventEmitter.emit('completionAgent', 0);
        // if (process.send) {
        //     process.send({type: 'completion', code: 0});
        // }

        const messages: any = [
            {"role": "assistant", "content": "You are a helpfull assistant"},
            {"role": "user", "content": "What is 3+4"}
        ];

        const reply = await env.completion(messages, "llama-v3p1-70b-instruct");
        console.log('Agent output:', reply);

    } catch (error) {
        console.error('Agent error:', error);
    }
}

// Add this at the bottom
if (import.meta.url.endsWith(process.argv[1])) {
    run();
}