import { type Metadata } from 'next';

import { Competition } from '@/components/Competition';
import { Markdown } from '@/components/lib/Markdown';

const content = `
Welcome to the first NEAR AI competition.

In this competition, we want the participants to pre-train a 0.5B parameter model that has the lowest perplexity as measured on a hold-out subset of FineWeb.

0.5B parameter model is quite small in the model world, but it can be trained relatively quickly, and thus allows iterating over various ideas and techniques. We will host more competition for large models, and scaling laws, in the new future. Learn more about this strategy [on the NEAR AI blog](https://near.ai).

To participate, you will need \`nearai\` installed on your computer. For details and documentation, visit the [nearai GitHub page](https://github.com/nearai/nearai).

From your machine you will use \`nearai submit\` to submit your runs. From within the run, you will use \`nearai\` to download raw data and to upload datasets and pre-trained models, as well as to run evaluations.

To participate in the competition, apply [here](https://docs.google.com/forms/d/e/1FAIpQLScInS4mHyZb_kSkD0-CMPPagyhpBKdutbAyS6YNbHJc9ZgaUw/viewform).
`;

const title = '0.5B Model Training Competition';

export const metadata: Metadata = {
  title,
};

export default function CompetitionPage() {
  return (
    <Competition
      competitionId="competition_0.5b"
      title={title}
      schedule="Dec 10th - Jan 15th, 2025 @ 11:59 PM UTC"
    >
      <Markdown content={content} />
    </Competition>
  );
}
