'use client';

import CompetitionPage from '~/app/competitions/[competition]/CompetitionPage';
import { Markdown } from '~/components/lib/Markdown';

export default function ModelTrainingPage() {
  const content = `
Welcome to the first NEAR AI competition.

In this competition, we want the participants to pre-train a 0.5B parameter model that has the lowest perplexity as measured on a hold-out subset of FineWeb.

0.5B parameter model is quite small in the model world, but it can be trained relatively quickly, and thus allows iterating over various ideas and techniques. We will host more competition for large models, and scaling laws, in the new future. Learn more about this strategy [on the NEAR AI blog](https://near.ai).

To participate, you will need \`nearai\` installed on your computer. For details and documentation, visit the [nearai GitHub page](https://github.com/nearai/nearai).

From your machine you will use \`nearai submit\` to submit your runs. From within the run, you will use \`nearai\` to download raw data and to upload datasets and pre-trained models, as well as to run evaluations.

To participate in the competition, apply [here](https://docs.google.com/forms/d/e/1FAIpQLScInS4mHyZb_kSkD0-CMPPagyhpBKdutbAyS6YNbHJc9ZgaUw/viewform).
`;
  return (
    <CompetitionPage title="0.5B Model Training Competition - January 2025">
      <Markdown content={content} />
    </CompetitionPage>
  );
}
