import { Button } from "~/components/ui/button";
import { PLAIN_MSG, RECIPIENT, NONCE } from "~/hooks/mutations";

export function NearAccount() {

  const requestSignature = () => {
    const fullUrl = window.location.href;
    const urlObj = new URL(fullUrl);
    const callbackUrl = `${urlObj.origin}${urlObj.pathname}`;

    const urlParams = new URLSearchParams({
      message: PLAIN_MSG,
      recipient: RECIPIENT,
      nonce: NONCE,
      callbackUrl,
    });

    window.location.replace(`https://auth.near.ai/?${urlParams.toString()}`);
  }

  return (
    <div>
        <Button
          onClick={() => {
            requestSignature()
          }}
          type="button"
        >
          NEAR Log In
        </Button>
    </div>
  );
}
