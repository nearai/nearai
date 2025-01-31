import {globalEnv} from './global-env.js';
//import {AgentEnvironment} from './agent-environment.js';


// Add this at the bottom of the file
let is_args = import.meta.url.endsWith(process.argv[1]);
if (!is_args) {

    throw new Error('No init args');
}

const agentPath = process.argv[2];
if (!agentPath) {
    throw new Error('Missing agent path');
}


// console.log("Staring ", agentPath)

const jsonString = process.argv[3];

if (!jsonString) {
    throw new Error('No configuration provided');
}

globalEnv.initialize(jsonString, agentPath);

// const agentEnv = new AgentEnvironment();
// agentEnv.runAgent(agentPath).catch(err => console.error('Fatal error:', err));


//let run_required = configManager.initialize(jsonString);

// export const nearClient = configManager.getNearClient();
/*
export const initializedClient = configManager.getSecureClient();

console.log("Starting agent with params:", jsonString);

if (run_required) {
    new AgentEnvironment()
        .runAgent(agentPath)
        .catch(err => console.error('Fatal error:', err));

}*/