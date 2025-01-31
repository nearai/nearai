export const env = {
    read_file: (path) => {
        return new Promise((resolve, reject) => {
            const correlationId = Math.random().toString(36).slice(2);
            const timeout = setTimeout(() => {
                reject(new Error('File read timeout'));
                process.off('message', handler);
            }, 5000);
            const handler = (msg) => {
                if (msg.correlationId === correlationId) {
                    clearTimeout(timeout);
                    process.off('message', handler);
                    if (msg.type === 'file_response') {
                        resolve(msg.payload);
                    }
                    else {
                        reject(new Error(msg.payload));
                    }
                }
            };
            process.on('message', handler);
            process.send({
                type: 'read_file',
                payload: { path },
                correlationId
            });
        });
    }
};
