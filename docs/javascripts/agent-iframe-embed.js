const isLocalEnv =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

function initialize() {
  setIframeSrc();
}

const MESSAGE = "Welcome to NEAR AI Hub!";
const RECIPIENT = "ai.near";
const SIGN_IN_CALLBACK_PATH = "/sign-in/callback";
const SIGN_IN_RESTORE_URL_KEY = "signInRestoreUrl";
const SIGN_IN_NONCE_KEY = "signInNonce";
const AUTH_NEAR_URL = "https://auth.near.ai";

function generateNonce() {
  const nonce = Date.now().toString();
  return nonce.padStart(32, "0");
}

function signInWithNear() {
  const nonce = generateNonce();

  localStorage.setItem(
    SIGN_IN_RESTORE_URL_KEY,
    `${location.pathname}${location.search}`
  );

  localStorage.setItem(SIGN_IN_NONCE_KEY, nonce);

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
  const url = localStorage.getItem(SIGN_IN_RESTORE_URL_KEY) || "/";
  if (url.startsWith(SIGN_IN_CALLBACK_PATH)) return "/";
  return url;
}

function createAuthNearLink(message, recipient, nonce, callbackUrl) {
  const urlParams = new URLSearchParams({
    message,
    recipient,
    nonce,
    callbackUrl,
  });

  return `${AUTH_NEAR_URL}/?${urlParams.toString()}`;
}

function redirectToAuthNearLink(message, recipient, nonce, callbackUrl) {
  const url = createAuthNearLink(message, recipient, nonce, callbackUrl);
  window.location.href = url;
}

function extractSignatureFromHashParams() {
  const hashParams = new URLSearchParams(location.hash.substring(1));

  if (!hashParams.get("signature")) {
    return null;
  }

  return {
    accountId: hashParams.get("accountId"),
    publicKey: hashParams.get("publicKey"),
    signature: hashParams.get("signature"),
  };
}

// Handle callback
async function handleCallback() {
  if (window.location.pathname.endsWith(SIGN_IN_CALLBACK_PATH)) {
    try {
      const hashParams = extractSignatureFromHashParams();
      const nonce = returnSignInNonce();

      if (!hashParams || !nonce) {
        throw new Error("Invalid auth params");
      }

      const auth = {
        account_id: hashParams.accountId,
        public_key: hashParams.publicKey,
        signature: hashParams.signature,
        message: MESSAGE,
        recipient: RECIPIENT,
        nonce: nonce,
      };

      // Store auth
      document.cookie = `${AUTH_COOKIE_NAME}=${JSON.stringify(
        auth
      )}; path=/; max-age=3600`;

      // Clear nonce
      clearSignInNonce();

      // Redirect back
      const restoreUrl = returnUrlToRestoreAfterSignIn();
      // Handle docs path
      window.location.href = restoreUrl.startsWith("/")
        ? window.location.origin + "/nearai" + restoreUrl
        : restoreUrl;
    } catch (error) {
      console.error("Auth error:", error);
      window.location.href = window.location.origin + "/nearai/";
    }
  }
}

function setIframeSrc() {
  const agentId = "gagdiez.near/docs-gpt/latest";
  const hostname = isLocalEnv
    ? "https://ai-hub-staging-f883t65pn-near-ai.vercel.app" // "http://localhost:3000"
    : "https://app.near.ai";
  const url = `${hostname}/embed/${agentId}?showThreads=true&showOutputAndEnvVars=true`;
  const iframe = document.querySelector(".agent-iframe");
  iframe?.setAttribute("src", url);
}

window.addEventListener("load", () => {
  initialize();
});
