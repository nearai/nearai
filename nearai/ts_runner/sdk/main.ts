import {globalEnv} from './global-env.js';

// Add this at the bottom of the file
let is_args = import.meta.url.endsWith(process.argv[1]);
if (!is_args) {

    throw new Error('No init args');
}

const agentPath = process.argv[2];
if (!agentPath) {
    throw new Error('Missing agent path');
}

const jsonString = process.argv[3];

if (!jsonString) {
    throw new Error('No configuration provided');
}

globalEnv.initialize(jsonString, agentPath);