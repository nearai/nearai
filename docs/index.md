# NEAR AI: Building a Truly Open AI

Welcome! [NEAR AI](https://near.ai) is a toolkit to help build, measure, and deploy AI systems focused on [agents](./agents/quickstart.md).

Driven by one of the minds behinds **TensorFlow** and the **Transformer Architecture**, NEAR AI puts you back in control. Your data stays yours, and your AI works for you, with no compromises on privacy or ownership.

---

<!DOCTYPE html>
<html>
<head>
    <script>
    // Auth constants matching demo
    const MESSAGE = 'Welcome to NEAR AI Hub!';
    const RECIPIENT = 'ai.near';
    const AUTH_COOKIE_NAME = 'near_ai_auth';
    const SIGN_IN_CALLBACK_PATH = '/sign-in/callback';
    const SIGN_IN_RESTORE_URL_KEY = 'signInRestoreUrl';
    const SIGN_IN_NONCE_KEY = 'signInNonce';
    const AUTH_NEAR_URL = 'https://auth.near.ai';

    // Generate nonce using timestamp like demo
    function generateNonce() {
        const nonce = Date.now().toString();
        return nonce.padStart(32, '0');
    }

    function signInWithNear() {
        const nonce = generateNonce();

        // Store current URL to restore after sign in
        localStorage.setItem(
            SIGN_IN_RESTORE_URL_KEY,
            `${location.pathname}${location.search}`
        );

        localStorage.setItem(SIGN_IN_NONCE_KEY, nonce);

        // Small delay to ensure storage is set
        setTimeout(() => {
            redirectToAuthNearLink(
                MESSAGE,
                RECIPIENT,
                nonce,
                returnSignInCallbackUrl()
            );
        }, 10);
    }

    function returnSignInCallbackUrl() {
        return location.origin + SIGN_IN_CALLBACK_PATH;
    }

    function returnSignInNonce() {
        return localStorage.getItem(SIGN_IN_NONCE_KEY);
    }

    function clearSignInNonce() {
        return localStorage.removeItem(SIGN_IN_NONCE_KEY);
    }

    function returnUrlToRestoreAfterSignIn() {
        const url = localStorage.getItem(SIGN_IN_RESTORE_URL_KEY) || '/';
        if (url.startsWith(SIGN_IN_CALLBACK_PATH)) return '/';
        return url;
    }

    function createAuthNearLink(
        message,
        recipient,
        nonce,
        callbackUrl
    ) {
        const urlParams = new URLSearchParams({
            message,
            recipient, 
            nonce,
            callbackUrl
        });

        return `${AUTH_NEAR_URL}/?${urlParams.toString()}`;
    }

    function redirectToAuthNearLink(
        message,
        recipient,
        nonce, 
        callbackUrl
    ) {
        const url = createAuthNearLink(message, recipient, nonce, callbackUrl);
        window.location.href = url;
    }

    function extractSignatureFromHashParams() {
        const hashParams = new URLSearchParams(location.hash.substring(1));
        
        if (!hashParams.get('signature')) {
            return null;
        }

        return {
            accountId: hashParams.get('accountId'),
            publicKey: hashParams.get('publicKey'),
            signature: hashParams.get('signature')
        };
    }

    // Handle callback
    async function handleCallback() {
        if (window.location.pathname.endsWith(SIGN_IN_CALLBACK_PATH)) {
            try {
                const hashParams = extractSignatureFromHashParams();
                const nonce = returnSignInNonce();
                
                if (!hashParams || !nonce) {
                    throw new Error('Invalid auth params');
                }

                const auth = {
                    account_id: hashParams.accountId,
                    public_key: hashParams.publicKey,
                    signature: hashParams.signature,
                    message: MESSAGE,
                    recipient: RECIPIENT,
                    nonce: nonce
                };

                // Store auth
                document.cookie = `${AUTH_COOKIE_NAME}=${JSON.stringify(auth)}; path=/; max-age=3600`;
                
                // Clear nonce
                clearSignInNonce();
                
                // Redirect back
                const restoreUrl = returnUrlToRestoreAfterSignIn();
                // Handle docs path
                window.location.href = restoreUrl.startsWith('/') ? 
                    window.location.origin + '/nearai' + restoreUrl : 
                    restoreUrl;
            } catch (error) {
                console.error('Auth error:', error);
                window.location.href = window.location.origin + '/nearai/';
            }
        }
    }

    // Initialize
    window.addEventListener('load', () => {
        handleCallback();
    });
    </script>
    <style>
        .agent-iframe {
            width: 100%;
            height: 600px;
            border: none;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        .connect-btn {
            display: inline-block;
            padding: 8px 16px;
            margin-bottom: 16px;
            background: #00C08B;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .connect-btn:hover {
            background: #00B081;
        }
    </style>
    
</head>
<body>
    <button id="connect-btn" class="connect-btn" onclick="signInWithNear()">Connect NEAR Wallet</button>
    <iframe 
        src="https://app.near.ai/agents/gagdiez.near/docs-gpt/latest/run"
        class="agent-iframe"
        allow="microphone"
        title="NEAR AI Agent">
    </iframe>
</body>
</html>

<div class="grid cards" markdown>

-   :material-robot-happy: __NEAR AI Agents__

    ---

    Autonomous system that can interact with you and use
    tools to solve tasks

    <span style="display: flex; justify-content: space-between;">
    [:material-clock-fast: Quickstart](./agents/quickstart.md)
    [:material-file-chart: Registry](./agents/registry.md)
    [:material-tools: Tools](./agents/env/tools.md)
    </span>

-   :material-tooltip-text: __AI Models__

    ---

    Best in class AI models that you can use and fine-tune to solve
    your tasks

    <span style="display: flex; justify-content: space-between;">
    [:material-chart-areaspline: Benchmarks](./models/benchmarks_and_evaluations.md)
    [:material-tune: Fine-Tuning](./models/fine_tuning.md)
    </span>


-   :material-web: __Developer Hub__ :octicons-link-external-16:

    ---

    NEAR AI developer hub where you can discover and deploy agents, datasets, and models with ease. 

    <span style="display: flex; justify-content: space-between;">
    [:material-robot-happy: Agents](https://app.near.ai/agents)
    [:material-cogs: Models](https://app.near.ai/models)
    [:material-database: Datasets](https://app.near.ai/agents)
    </span>

-   :material-lightbulb-group: __Community__ :octicons-link-external-16:

    ---

    Join our community! Get help and contribute to the future of AI

    [:simple-telegram: Community](https://t.me/nearaialpha)

</div>

---

!!! warning "Alpha"

    NEAR AI is currently in `alpha` - we're building something special and shipping new features every day! Want to help shape the future of AI? Join our community and contribute! 🚀

    - 🐛 [Report bugs and suggest features](https://github.com/nearai/nearai/issues)
    - 💻 [Submit pull requests](https://github.com/nearai/nearai/pulls)
    - 📖 [Improve documentation](contributing.md/#contribute-documentation)
    - 🤝 [Help other users in the community](https://t.me/nearaialpha)
    - 🌟 [Star our repository](https://github.com/nearai/nearai)

    Check out our [contributing guide](contributing.md) to get started.

