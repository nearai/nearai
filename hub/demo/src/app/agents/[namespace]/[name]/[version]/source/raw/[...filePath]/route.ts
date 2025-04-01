import { type NextRequest } from 'next/server';

import { fetchRawFile, type FetchRawFileInput } from '@/routes/raw-file';

export async function GET(req: NextRequest, params: FetchRawFileInput) {
  return fetchRawFile(req, 'agent', params);
}
