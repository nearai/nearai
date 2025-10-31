'use client';

import { useState, useMemo } from 'react';
import { Section, Text, Flex, Grid, Card, Button } from '@near-pagoda/ui';
import { type z } from 'zod';
import { api } from '~/trpc/react';
import { type entryModel } from '~/lib/models';
import { EntryCard } from '~/components/EntryCard';
import s from '../page.module.scss';

export default function AgentsShowcasePage() {
  const agents = api.hub.entries.useQuery({
    category: 'agent',
  });

  const topAgents = useMemo(() => {
    return (
      (agents.data ?? [])
        .filter((a): a is z.infer<typeof entryModel> => a !== undefined)
        .sort((a, b) => b.num_stars - a.num_stars)
        .slice(0, 10) || []
    );
  }, [agents.data]);

  const newestAgents = useMemo(() => {
    return (
      (agents.data ?? [])
        .filter((a): a is z.infer<typeof entryModel> => a !== undefined && a.description !== undefined && a.category !== undefined && a.name !== undefined && a.namespace !== undefined && a.tags !== undefined && a.version !== undefined && a.id !== undefined && a.updated !== undefined)
        .sort((a, b) => new Date(b.updated).getTime() - new Date(a.updated).getTime())
        .slice(0, 10) || []
    );
  }, [agents.data]);

  return (
    <Section padding="hero" background="sand-1" gap="xl">
      <Flex direction="column" gap="m">
        <Text as="h2" size="text-2xl" weight="600">
          Top Agents
        </Text>
        <Carousel agents={topAgents} />
      </Flex>

      <Flex direction="column" gap="m">
        <Text as="h2" size="text-2xl" weight="600">
          Newest Agents
        </Text>
        <Carousel agents={newestAgents} />
      </Flex>
    </Section>
  );
}

type AgentType = z.infer<typeof entryModel>;



function Carousel({ agents }: { agents: AgentType[] }) {
    const agentData: Record<string, { backgroundImage: string | undefined }> = {
        agent1: { backgroundImage: 'url1' },
        agent2: { backgroundImage: 'url2' },
        // Add more agents as needed
    };
  const [currentIndex, setCurrentIndex] = useState(0);
  const itemsPerPage = 3;

  const handlePrevClick = () => {
    setCurrentIndex((prevIndex) => Math.max(prevIndex - itemsPerPage, 0));
  };

  const handleNextClick = () => {
    setCurrentIndex((prevIndex) => Math.min(prevIndex + itemsPerPage, agents.length - itemsPerPage));
  };

  const displayedAgents = agents.slice(currentIndex, currentIndex + itemsPerPage);

  return (
    <div className={s.carouselContainer}>
      <Button label="Prev" onClick={handlePrevClick} disabled={currentIndex === 0}>Prev
      </Button>
      <Grid gap="m" columns="1fr 1fr 1fr" tablet={{ columns: '1fr 1fr' }} phone={{ columns: '1fr' }}>
        {displayedAgents.map((agent) =>
          agent && agent.id ? (
            <Card
              key={agent.id}
              background="sand-0"
              padding="l"
              gap="l"
              className={s.agentCard}
            >
              <div
                className={s.agentBackground}
                style={{
                  backgroundImage: `url(${agentData[String(agent.id)]?.backgroundImage || ''})`,
                }}
              />
              {agent && <EntryCard entry={agent} />}
              <Text size="text-s" color="sand-12">
                {agent?.description ?? 'No description available'}
              </Text>
            </Card>
          ) : null
        )}
      </Grid>
      <Button label="Next" onClick={handleNextClick} disabled={currentIndex >= agents.length - itemsPerPage}>Next
      </Button>
    </div>
  );
}