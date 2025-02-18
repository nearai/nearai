'use client';

import { Button, Flex, Text } from '@near-pagoda/ui';
import { type z } from 'zod';

import { useThreadsStore } from '~/stores/threads';

import { Message } from './Message';
import {
    type quoteSchema,
} from './schema/quote';
import { useWalletStore } from '~/stores/wallet';
import { formatDollar } from '@near-pagoda/ui/utils';
import { useState } from 'react';

type Props = {
    content: z.infer<typeof quoteSchema>['quote'];
};

enum PaymentStatus {
    NONE = 'none',
    PENDING = 'pending',
    SUCCESS = 'success',
    FAILED = 'failed',
}

const NEAR_USDC_CONTRACT_ID = '17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1';

export const QuoteConfirmation = ({ content }: Props) => {
    const addMessage = useThreadsStore((store) => store.addMessage);
    const wallet = useWalletStore((store) => store.wallet);
    const modal = useWalletStore((store) => store.modal);
    const account = useWalletStore((store) => store.account);

    const [paymentStatus, setPaymentStatus] = useState(PaymentStatus.NONE);
    const [loading, setLoading] = useState(false);

    if (content.type !== 'Quote') {
        console.error(
            `Attempted to render <QuoteConfirmation /> with invalid content type: ${content.type}`,
        );
        return null;
    }

    const submitPaymentConfirmation = async (
    ) => {
        if (!addMessage) return;
        if (!wallet) return;

        const amount = content.payment_plans?.[0]?.amount;
        if (!amount) return;

        const message: Parameters<typeof wallet.signAndSendTransaction>[0] = {
            signerId: account?.accountId,
            receiverId: NEAR_USDC_CONTRACT_ID,
            actions: [
                // {
                //     type: "FunctionCall",
                //     params: {
                //         methodName: "storage_deposit",
                //         args: {
                //             account_id: account?.accountId,
                //             registration_only: true
                //         },
                //         gas: BigInt(300000000000000).toString(), // 300 TGas
                //         deposit: BigInt(1250000000000000000000).toString() // 0.00125 NEAR
                //     }
                // },
                {
                    type: "FunctionCall",
                    params: {
                        methodName: "ft_transfer",
                        args: {
                            receiver_id: content.payee_id,
                            amount: (amount * 1000000).toString(),
                            memo: "Test USDC Transfer"
                        },
                        gas: BigInt(300000000000000).toString(),
                        deposit: BigInt(1).toString(),
                    }
                }
            ],
        };

        try {
            setLoading(true);
            const result = await wallet.signAndSendTransaction(message);
            if (!result) {
                setPaymentStatus(PaymentStatus.FAILED);
            } else if (result.status === 'Failure') {
                setPaymentStatus(PaymentStatus.FAILED);
            } else {
                setPaymentStatus(PaymentStatus.SUCCESS);
            }
            void addMessage({
                new_message: JSON.stringify({
                    yay: 'yay',
                }),
            });
        } catch (error) {
            setPaymentStatus(PaymentStatus.FAILED);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Message>
            <Flex direction="column" gap="s">
                <Text size="text-l">Payment authorization required</Text>
                <Text size="text-s">Amount: {formatDollar(content.payment_plans?.[0]?.amount)}</Text>
            </Flex>

            {
                (paymentStatus !== PaymentStatus.SUCCESS) && (
                    <Flex align="center" gap="s" wrap="wrap">
                        {((wallet) ? (
                            <Button
                                label="Confirm Payment"
                                variant="affirmative"
                                onClick={() => submitPaymentConfirmation()}
                                loading={loading}
                            />
                        ) : (
                            <Button
                                label="Connect Wallet"
                                variant="secondary"
                                onClick={() => modal?.show()}
                            />
                        ))}
                    </Flex>
                )
            }
            {
                paymentStatus === PaymentStatus.FAILED && (
                    <Text size="text-s">Payment failed :(</Text>
                )
            }
        </Message>
    );
};
