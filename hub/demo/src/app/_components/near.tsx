import { Button } from "~/components/ui/button";
import { CALLBACK_URL, NONCE, PLAIN_MSG, RECIPIENT } from "~/hooks/mutations";

export function NearLogin() {
  const requestSignature = () => {
    const urlParams = new URLSearchParams({
      message: PLAIN_MSG,
      recipient: RECIPIENT,
      nonce: NONCE,
      callbackUrl: CALLBACK_URL,
    });

    window.location.replace(`https://auth.near.ai/?${urlParams.toString()}`);
  };

  return (
    <div>
      <Button
        onClick={() => {
          requestSignature();
        }}
        className="w-full"
        type="button"
      >
        NEAR Log In
      </Button>
    </div>
  );
}
