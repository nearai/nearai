import { Button } from "~/components/ui/button";
import { CALLBACK_URL, MESSAGE, RECIPIENT } from "~/hooks/mutations";
import { generateNonce, redirectToAuthNearLink } from "~/lib/auth";
import usePersistingStore from "~/store/store";

export function NearLogin() {
  const store = usePersistingStore();

  const requestSignature = async () => {
    const nonce = generateNonce();
    store.setCurrentNonce(nonce);
    redirectToAuthNearLink(MESSAGE, RECIPIENT, nonce, CALLBACK_URL);
  };

  return (
    <div>
      <Button
        onClick={async () => {
          await requestSignature();
        }}
        className="w-full"
        type="button"
      >
        NEAR Log In
      </Button>
    </div>
  );
}
