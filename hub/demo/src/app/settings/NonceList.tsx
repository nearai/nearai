import {
  Badge,
  Button,
  Dropdown,
  Flex,
  SvgIcon,
  Table,
  Text,
  Timestamp,
} from '@nearai/ui';
import { DotsThree, Prohibit } from '@phosphor-icons/react';
import { useEffect } from 'react';

import { RECIPIENT, REVOKE_ALL_MESSAGE, REVOKE_MESSAGE } from '@/lib/auth';
import {
  extractSignatureFromHashParams,
  generateNonce,
  openAuthUrl,
} from '@/lib/auth';
import { authorizationModel } from '@/lib/models';
import { trpc } from '@/trpc/TRPCProvider';

export const NonceList = () => {
  const noncesQuery = trpc.hub.nonces.useQuery();
  const revokeNonceMutation = trpc.hub.revokeNonce.useMutation();
  const revokeAllNoncesMutation = trpc.hub.revokeAllNonces.useMutation();

  const startRevokeNonce = (revokeNonce?: string) => {
    const nonce = generateNonce();

    let callbackUrl = location.origin + '/settings?nonce=' + nonce;
    if (revokeNonce) {
      callbackUrl += '&revoke_nonce=' + revokeNonce;
      openAuthUrl(REVOKE_MESSAGE, RECIPIENT, nonce, callbackUrl);
    } else {
      // If no nonce is provided, it will revoke all nonces
      openAuthUrl(REVOKE_ALL_MESSAGE, RECIPIENT, nonce, callbackUrl);
    }
  };

  useEffect(() => {
    const hashParams = extractSignatureFromHashParams();
    if (!hashParams) return;

    // in url params, not hash params
    const params = new URLSearchParams(location.search);
    const revokeNonce = params.get('revoke_nonce');
    const signingNonce = params.get('nonce');

    // cleanup url, remove hash params
    const cleanUrl = location.pathname + location.search;
    window.history.replaceState(null, '', cleanUrl);

    if (!signingNonce) return;

    let message = REVOKE_ALL_MESSAGE;
    if (revokeNonce) {
      message = REVOKE_MESSAGE;
    }

    const auth = authorizationModel.parse({
      account_id: hashParams.accountId,
      public_key: hashParams.publicKey,
      signature: hashParams.signature,
      callback_url: location.origin + location.pathname + location.search,
      message: message,
      recipient: RECIPIENT,
      nonce: signingNonce,
    });

    const revokeNonceFn = async (nonce: string) => {
      try {
        await revokeNonceMutation.mutateAsync({
          nonce: nonce,
          auth: `Bearer ${JSON.stringify(auth)}`,
        });
      } catch (e) {
        console.error(e);
      } finally {
        await noncesQuery.refetch();
      }
    };

    const revokeAllNoncesFn = async () => {
      try {
        await revokeAllNoncesMutation.mutateAsync({
          auth: `Bearer ${JSON.stringify(auth)}`,
        });
      } catch (e) {
        console.error(e);
      } finally {
        await noncesQuery.refetch();
      }
    };

    if (revokeNonce) {
      void revokeNonceFn(revokeNonce);
    } else {
      void revokeAllNoncesFn();
    }
  });

  return (
    <Flex direction="column" gap="m">
      <Flex align="center" gap="m">
        <Text as="h2" style={{ marginRight: 'auto' }}>
          Nonces
        </Text>

        <Button
          variant="destructive"
          label="Revoke All"
          size="small"
          onClick={() => startRevokeNonce()}
          loading={revokeAllNoncesMutation.isPending}
        />
      </Flex>

      <Table.Root>
        <Table.Head>
          <Table.Row>
            <Table.HeadCell>Nonce</Table.HeadCell>
            <Table.HeadCell>Account ID</Table.HeadCell>
            <Table.HeadCell>Message</Table.HeadCell>
            <Table.HeadCell>Recipient</Table.HeadCell>
            <Table.HeadCell>Callback URL</Table.HeadCell>
            <Table.HeadCell>First Seen At</Table.HeadCell>
            <Table.HeadCell>Status</Table.HeadCell>
            <Table.HeadCell></Table.HeadCell>
          </Table.Row>
        </Table.Head>

        <Table.Body>
          {!noncesQuery.data && <Table.PlaceholderRows />}

          {noncesQuery.data?.map((nonce) => (
            <Table.Row key={nonce.nonce}>
              <Table.Cell>
                <Text size="text-xs" color="sand-12">
                  {nonce.nonce}
                </Text>
              </Table.Cell>
              <Table.Cell>
                <Text size="text-xs">{nonce.account_id}</Text>
              </Table.Cell>
              <Table.Cell style={{ minWidth: '10rem' }}>
                <Text size="text-xs">{nonce.message}</Text>
              </Table.Cell>
              <Table.Cell>
                <Text size="text-xs">{nonce.recipient}</Text>
              </Table.Cell>
              <Table.Cell>
                <Text size="text-xs">{nonce.callback_url}</Text>
              </Table.Cell>
              <Table.Cell>
                <Text size="text-xs" noWrap>
                  <Timestamp date={new Date(nonce.first_seen_at)} />
                </Text>
              </Table.Cell>
              <Table.Cell>
                {nonce.nonce_status === 'revoked' ? (
                  <Badge variant="alert" label="Revoked" />
                ) : (
                  <Badge variant="success" label="Active" />
                )}
              </Table.Cell>
              <Table.Cell style={{ width: '1px' }}>
                <Dropdown.Root>
                  <Dropdown.Trigger asChild>
                    <Button
                      label="Actions"
                      icon={<DotsThree weight="bold" />}
                      fill="outline"
                      size="small"
                      onClick={() => startRevokeNonce(nonce.nonce)}
                      disabled={revokeNonceMutation.isPending}
                    />
                  </Dropdown.Trigger>

                  <Dropdown.Content>
                    <Dropdown.Section>
                      <Dropdown.Item
                        onSelect={() => startRevokeNonce(nonce.nonce)}
                        disabled={nonce.nonce_status === 'revoked'}
                      >
                        <SvgIcon color="red-9" icon={<Prohibit />} />
                        {nonce.nonce_status === 'revoked'
                          ? 'Nonce Revoked'
                          : 'Revoke Nonce'}
                      </Dropdown.Item>
                    </Dropdown.Section>
                  </Dropdown.Content>
                </Dropdown.Root>
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
    </Flex>
  );
};
