export const MAINNET_NEAR_USDC_CONTRACT_ID =
  '17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1';

const USDC_ATOMIC_UNITS_DECIMAL_FACTOR = 1_000_000; // 6 decimal places

export function usdcAtomicAmountToDollars(amount: number) {
  return amount / USDC_ATOMIC_UNITS_DECIMAL_FACTOR;
}

export function dollarsToUsdcAtomicAmount(amount: number) {
  return amount * USDC_ATOMIC_UNITS_DECIMAL_FACTOR;
}
