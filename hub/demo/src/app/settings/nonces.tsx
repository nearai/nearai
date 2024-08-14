import { useEffect } from "react";
import { Button } from "~/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "~/components/ui/table";
import { Two } from "~/components/ui/typography";
import {
  CALLBACK_URL,
  RECIPIENT,
  REVOKE_ALL_MESSAGE,
  REVOKE_MESSAGE,
} from "~/hooks/mutations";
import {
  extractSignatureFromHashParams,
  generateNonce,
  redirectToAuthNearLink,
} from "~/lib/auth";
import { authorizationModel } from "~/lib/models";
import { api } from "~/trpc/react";

export default function ListNonces() {
  const nonces = api.hub.listNonces.useQuery();
  const revokeNonceMut = api.hub.revokeNonce.useMutation();
  const revokeAllNoncesMut = api.hub.revokeAllNonces.useMutation();

  const startRevokeNonce = (revokeNonce?: string) => {
    const nonce = generateNonce();

    let callbackUrl = CALLBACK_URL + "/settings?nonce=" + nonce;
    if (revokeNonce) {
      callbackUrl += "&revoke_nonce=" + revokeNonce;
      redirectToAuthNearLink(REVOKE_MESSAGE, RECIPIENT, nonce, callbackUrl);
    } else {
      // If no nonce is provided, it will revoke all nonces
      redirectToAuthNearLink(REVOKE_ALL_MESSAGE, RECIPIENT, nonce, callbackUrl);
    }
  };

  useEffect(() => {
    const hashParams = extractSignatureFromHashParams();
    if (!hashParams) return;
    // cleanup url, remove hash params
    const cleanUrl = window.location.pathname + window.location.search;
    window.history.replaceState(null, "", cleanUrl);

    // in url params, not hash params
    const params = new URLSearchParams(window.location.search);
    const revokeNonce = params.get("revoke_nonce");
    const signingNonce = params.get("nonce");

    if (!signingNonce) return;

    let message = REVOKE_ALL_MESSAGE;
    if (revokeNonce) {
      message = REVOKE_MESSAGE;
    }

    const auth = authorizationModel.parse({
      account_id: hashParams.accountId,
      public_key: hashParams.publicKey,
      signature: hashParams.signature,
      callback_url: CALLBACK_URL + cleanUrl,
      message: message,
      recipient: RECIPIENT,
      nonce: signingNonce,
    });

    const revokeNonceFn = async (revokeNonce: string) => {
      try {
        await revokeNonceMut.mutateAsync({
          nonce: revokeNonce,
          auth: `Bearer ${JSON.stringify(auth)}`,
        });
      } catch (e) {
        console.error(e);
      } finally {
        await nonces.refetch();
      }
    };

    const revokeAllNoncesFn = async () => {
      try {
        await revokeAllNoncesMut.mutateAsync({
          auth: `Bearer ${JSON.stringify(auth)}`,
        });
      } catch (e) {
        console.error(e);
      } finally {
        await nonces.refetch();
      }
    };

    if (revokeNonce) {
      void revokeNonceFn(revokeNonce);
    } else {
      void revokeAllNoncesFn();
    }
  });

  return (
    <div>
      <Two classname="flex justify-between">
        <span>Nonces</span>
        <Button
          variant={"destructive"}
          onClick={() => startRevokeNonce()}
          disabled={!revokeAllNoncesMut.isIdle}
        >
          Revoke all nonces
        </Button>
      </Two>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nonce</TableHead>
            <TableHead>Account ID</TableHead>
            <TableHead>Message</TableHead>
            <TableHead>Recipient</TableHead>
            <TableHead>Callback URL</TableHead>
            <TableHead>Nonce Status</TableHead>
            <TableHead>First Seen At</TableHead>
            <TableHead className="text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {nonces.data?.map((nonce) => (
            <TableRow key={nonce.nonce}>
              <TableCell>{nonce.nonce}</TableCell>
              <TableCell>{nonce.account_id}</TableCell>
              <TableCell>{nonce.message}</TableCell>
              <TableCell>{nonce.recipient}</TableCell>
              <TableCell className="break-all">{nonce.callback_url}</TableCell>
              <TableCell>{nonce.nonce_status}</TableCell>
              <TableCell>{nonce.first_seen_at}</TableCell>
              <TableCell className="text-right">
                <Button
                  variant={"destructive"}
                  onClick={() => startRevokeNonce(nonce.nonce)}
                  disabled={
                    revokeNonceMut.isPending || nonce.nonce_status === "revoked"
                  }
                >
                  Revoke
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
