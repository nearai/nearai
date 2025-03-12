import { env } from './env';

export const APP_TITLE = env.NEXT_PUBLIC_CONSUMER_MODE
  ? 'Assistant'
  : 'Developer Hub';
