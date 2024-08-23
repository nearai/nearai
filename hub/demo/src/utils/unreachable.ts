export function unreachable(
  x: never,
  extract?: (input: unknown) => string,
): never {
  throw new Error(`Unreachable Case: ${extract ? extract(x) : x}`);
}
