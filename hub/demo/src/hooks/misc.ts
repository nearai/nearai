import { CALLBACK_URL, PLAIN_MSG, RECIPIENT, NONCE } from "./mutations";
import { authorizationModel } from "~/lib/models";

function parseHashParams(hash: string) {
  const hashParams = new URLSearchParams(hash.substring(1));
  const params: Record<string, string> = {};
  hashParams.forEach((value, key) => {
    params[key] = value;
  });
  return params;
}

function stringToUint8Array (str: string) {
  const encoder = new TextEncoder();
  const bytes = encoder.encode(str);
  return new Uint8Array(bytes);
}

export function useHandleRedirectFromWallet() {
  const hashParams = parseHashParams(location.hash);
    if (hashParams.signature) {
      const auth = authorizationModel.parse({
        account_id: hashParams.accountId,
        public_key: hashParams.publicKey,
        signature: hashParams.signature,
        callback_url: CALLBACK_URL,
        plainMsg: PLAIN_MSG,
        recipient: RECIPIENT,
        nonce: [... stringToUint8Array(NONCE)]
      });
      localStorage.setItem("current_auth", `Bearer ${JSON.stringify(auth)}`);
    }
}
