function wait(ms: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export async function poll<T>(
  url: Parameters<typeof fetch>[0],
  fetchOptions: Parameters<typeof fetch>[1],
  pollOptions: {
    maxAttempts: number;
    attemptDelayMs: number;
  },
  shouldTerminateAndReturn: (
    response: Response,
    currentAttempt?: number,
  ) => Promise<T>,
) {
  let attempts = 0;
  let response: Response | null = null;

  while (attempts < pollOptions.maxAttempts) {
    await wait(pollOptions.attemptDelayMs);

    try {
      response = await fetch(url, {
        ...fetchOptions,
        cache: 'no-store',
      });

      const result = await shouldTerminateAndReturn(response, attempts);

      if (result) {
        return result;
      }
    } catch (error) {
      console.error(error);
    }

    attempts++;
  }

  throw new Error(
    `Polling timed out after ${pollOptions.maxAttempts} attempts`,
  );
}
