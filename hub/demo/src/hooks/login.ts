import { useEffect } from "react";
import { parseHashParams, stringToUint8Array } from "~/hooks/misc";
import { authorizationModel } from "~/lib/models";
import { CALLBACK_URL, NONCE, PLAIN_MSG, RECIPIENT } from "./mutations";
import usePersistingStore from "~/store/store";

/**
 * This hook is used to handle the login process
 * It will parse the hash params from the url, and set the auth value in the store
 */
export function useHandleLogin() {
  const store = usePersistingStore();

  return useEffect(() => {
    const hashParams = parseHashParams(location.hash);
    if (hashParams.signature) {
      const auth = authorizationModel.parse({
        account_id: hashParams.accountId,
        public_key: hashParams.publicKey,
        signature: hashParams.signature,
        callback_url: CALLBACK_URL,
        plainMsg: PLAIN_MSG,
        recipient: RECIPIENT,
        nonce: [...stringToUint8Array(NONCE)],
      });
      store.setAuthValueRaw(`Bearer ${JSON.stringify(auth)}`);

      // cleanup url
      window.history.replaceState(
        null,
        "",
        window.location.pathname + window.location.search,
      );
    }
  }, [store]);
}
