import { DotsThree, Prohibit } from '@phosphor-icons/react';
import { useEffect } from 'react';

import { Badge } from '~/components/lib/Badge';
import { Button } from '~/components/lib/Button';
import { Dropdown } from '~/components/lib/Dropdown';
import { Flex } from '~/components/lib/Flex';
import { SvgIcon } from '~/components/lib/SvgIcon';
import { Table } from '~/components/lib/Table';
import { Text } from '~/components/lib/Text';
import { Timestamp } from '~/components/lib/Timestamp';
import {
  CALLBACK_URL,
  RECIPIENT,
  REVOKE_ALL_MESSAGE,
  REVOKE_MESSAGE,
} from '~/lib/auth';
import {
  extractSignatureFromHashParams,
  generateNonce,
  redirectToAuthNearLink,
} from '~/lib/auth';
import { authorizationModel } from '~/lib/models';
import { api } from '~/trpc/react';

export const NonceList = () => {
  const nonces = api.hub.listNonces.useQuery();
  const revokeNonceMutation = api.hub.revokeNonce.useMutation();
  const revokeAllNoncesMutation = api.hub.revokeAllNonces.useMutation();

  const startRevokeNonce = (revokeNonce?: string) => {
    const nonce = generateNonce();

    let callbackUrl = CALLBACK_URL + '/settings?nonce=' + nonce;
    if (revokeNonce) {
      callbackUrl += '&revoke_nonce=' + revokeNonce;
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
    window.history.replaceState(null, '', cleanUrl);

    // in url params, not hash params
    const params = new URLSearchParams(window.location.search);
    const revokeNonce = params.get('revoke_nonce');
    const signingNonce = params.get('nonce');

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

    const revokeNonceFn = async (nonce: string) => {
      try {
        await revokeNonceMutation.mutateAsync({
          nonce: nonce,
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
        await revokeAllNoncesMutation.mutateAsync({
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
          {!nonces.data && <Table.PlaceholderRows />}

          {nonces.data?.map((nonce) => (
            <Table.Row key={nonce.nonce}>
              <Table.Cell>
                <Text size="text-xs" color="sand12" clampLines={1}>
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
                        <SvgIcon color="red8" icon={<Prohibit />} />
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