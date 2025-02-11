import { type z } from 'zod';

import { CURRENT_AGENT_PROTOCOL_SCHEMA } from '~/components/threads/messages/aitp/schema/base';
import { type requestDataSchema } from '~/components/threads/messages/aitp/schema/data';
import {
  type quoteSchema,
  type requestDecisionSchema,
} from '~/components/threads/messages/aitp/schema/decision';
import { type threadMessageModel } from '~/lib/models';

function generateMockedQuote(priceUsd: number): z.infer<typeof quoteSchema> {
  return {
    type: 'Quote',
    payee_id: 'foobar',
    quote_id: 'foobar',
    payment_plans: [
      {
        amount: priceUsd,
        currency: 'USD',
        plan_id: 'foobar',
        plan_type: 'one-time',
      },
    ],
    valid_until: '2050-01-01T00:00:00Z',
  };
}

export function generateMockedAITPMessages(threadId: string) {
  const requestDecisionCheckbox: z.infer<typeof requestDecisionSchema> = {
    $schema: CURRENT_AGENT_PROTOCOL_SCHEMA,
    request_decision: {
      id: crypto.randomUUID(),
      title: 'Your Favorite Colors',
      description: `Which colors are your favorite? This will help refine your product search.`,
      type: 'checkbox',
      options: [
        {
          id: 'blue',
          name: 'Blue',
          description: 'A calming color',
          image_url:
            'https://media.istockphoto.com/id/959093486/vector/blue-abstract-gradient-mesh-background.jpg?s=612x612&w=0&k=20&c=c6lozNEcfMBlPlZazHJiy4NnviEGkAPPgubKC-9GowI=',
        },
        {
          id: 'red',
          name: 'Red',
          description: 'An exciting color',
          image_url:
            'https://img.freepik.com/free-vector/dark-deep-red-gradient-background_78370-3496.jpg?semt=ais_hybrid',
        },
        {
          id: 'green',
          name: 'Green',
          description: 'An earthy color',
          image_url:
            'https://img.freepik.com/free-vector/gradient-background-green-tones_23-2148373477.jpg',
        },
      ],
    },
  };

  const requestDecisionRadio: z.infer<typeof requestDecisionSchema> = {
    $schema: CURRENT_AGENT_PROTOCOL_SCHEMA,
    request_decision: {
      id: crypto.randomUUID(),
      type: 'radio',
      description: 'Select your favorite number:',
      options: [
        {
          id: '0',
          name: '0',
        },
        {
          id: '7',
          name: '7',
        },
        {
          id: '100',
          name: '100',
        },
      ],
    },
  };

  const requestDecisionProducts: z.infer<typeof requestDecisionSchema> = {
    $schema: CURRENT_AGENT_PROTOCOL_SCHEMA,
    request_decision: {
      id: crypto.randomUUID(),
      title: 'Recommended Products',
      description: `Based on your selected factors, here are the best recommendations`,
      type: 'products',
      options: [
        {
          id: 'product_1',
          name: 'JBL Tour One M2',
          description: 'A short, summarized description about the headphones',
          five_star_rating: 4.2,
          reviews_count: 132,
          quote: generateMockedQuote(199.5),
          image_url:
            'https://m.media-amazon.com/images/I/61rJmoiiYHL._AC_SX679_.jpg',
          url: 'https://www.amazon.com/JBL-Tour-One-Cancelling-Headphones/dp/B0C4JBTM5B',
        },
        {
          id: 'product_2',
          name: 'Soundcore by Anker, Space One',
          short_variant_name: 'Space One',
          five_star_rating: 3.5,
          quote: generateMockedQuote(79.99),
          image_url:
            'https://m.media-amazon.com/images/I/51EXj4BRQaL._AC_SX679_.jpg',
          url: 'https://www.amazon.com/Soundcore-Cancelling-Headphones-Reduction-Comfortable/dp/B0C6KKQ7ND',
          variants: [
            {
              id: 'product_3',
              name: 'Soundcore by Anker, Jet Black',
              short_variant_name: 'Jet Black',
              five_star_rating: 3.75,
              quote: generateMockedQuote(89.99),
              image_url:
                'https://m.media-amazon.com/images/I/51l80KVua0L._AC_SX679_.jpg',
              url: 'https://www.amazon.com/Soundcore-Cancelling-Headphones-Reduction-Comfortable/dp/B0C6KFZC9Z',
            },
            {
              id: 'product_4',
              name: 'Soundcore by Anker, Cream',
              short_variant_name: 'Cream',
              five_star_rating: 3.75,
              quote: generateMockedQuote(74.99),
              image_url:
                'https://m.media-amazon.com/images/I/51QVszp82CL._AC_SX679_.jpg',
              url: 'https://www.amazon.com/Soundcore-Cancelling-Headphones-Reduction-Comfortable/dp/B0C6KJ3R71',
            },
          ],
        },
        {
          id: 'product_5',
          name: 'Sony WH-1000XM5',
          quote: generateMockedQuote(399.99),
          image_url:
            'https://m.media-amazon.com/images/I/61eeHPRFQ9L._AC_SX679_.jpg',
          url: 'https://www.amazon.com/Sony-WH-1000XM5-Headphones-Hands-Free-WH1000XM5/dp/B0BXYCS74H',
        },
        {
          id: 'product_5',
          name: 'Edifier STAX Spirit S3',
          quote: generateMockedQuote(348),
          image_url:
            'https://m.media-amazon.com/images/I/61E4YsCrICL._AC_SX679_.jpg',
          url: 'https://www.amazon.com/Sony-WH-1000XM5-Headphones-Hands-Free-WH1000XM5/dp/B0BXYCS74H',
        },
      ],
    },
  };

  const requestDecisionConfirmation: z.infer<typeof requestDecisionSchema> = {
    $schema: CURRENT_AGENT_PROTOCOL_SCHEMA,
    request_decision: {
      id: crypto.randomUUID(),
      title: 'Please confirm',
      description: `Would you like to eat all cookies?`,
      type: 'confirmation',
      options: [
        {
          id: '1',
          name: 'Yes, eat the cookies',
        },
        {
          id: '2',
          name: "No, that's not healthy",
        },
        {
          id: '3',
          name: 'Something else',
        },
      ],
    },
  };

  const requestDataShippingAddressInternationalAndMore: z.infer<
    typeof requestDataSchema
  > = {
    $schema: CURRENT_AGENT_PROTOCOL_SCHEMA,
    request_data: {
      id: crypto.randomUUID(),
      title: 'Shipping Info (International + Favorites)',
      description: `Great! Let's start with your shipping info.`,
      fillButtonLabel: 'Fill out shipping info',
      forms: [
        {
          json_url:
            'https://app.near.ai/api/v1/aitp/request_data/forms/shipping_address_international.json',
        },
        {
          description:
            'Share more info about yourself to improve your shopping experience.',
          fields: [
            {
              id: 'favorite_color',
              label: 'Favorite Color',
              type: 'select',
              options: ['Blue', 'Orange', 'White'],
              required: true,
            },
            {
              id: 'favorite_number',
              label: 'Favorite Number',
              type: 'number',
              default_value: '7',
              required: false,
            },
          ],
        },
      ],
    },
  };

  const requestDataShippingAddressUs: z.infer<typeof requestDataSchema> = {
    $schema: CURRENT_AGENT_PROTOCOL_SCHEMA,
    request_data: {
      id: crypto.randomUUID(),
      title: 'Shipping Info (US)',
      description: `Great! Let's start with your shipping info.`,
      fillButtonLabel: 'Fill out shipping info',
      forms: [
        {
          json_url:
            'https://app.near.ai/api/v1/aitp/request_data/forms/shipping_address_us.json',
        },
      ],
    },
  };

  const message: z.infer<typeof threadMessageModel> = {
    content: [
      {
        type: 'text',
        text: {
          annotations: [],
          value: JSON.stringify(requestDecisionCheckbox),
        },
      },
      {
        type: 'text',
        text: {
          annotations: [],
          value: JSON.stringify(requestDecisionRadio),
        },
      },
      {
        type: 'text',
        text: {
          annotations: [],
          value: JSON.stringify(requestDecisionProducts),
        },
      },
      {
        type: 'text',
        text: {
          annotations: [],
          value: JSON.stringify(requestDecisionConfirmation),
        },
      },
      {
        type: 'text',
        text: {
          annotations: [],
          value: JSON.stringify(requestDataShippingAddressInternationalAndMore),
        },
      },
      {
        type: 'text',
        text: {
          annotations: [],
          value: JSON.stringify(requestDataShippingAddressUs),
        },
      },
      {
        type: 'text',
        text: {
          annotations: [],
          value: JSON.stringify({
            foo: 123,
            bar: {
              baz: true,
            },
          }),
        },
      },
    ],
    attachments: [],
    completed_at: 0,
    created_at: 0,
    id: 'abc-123',
    incomplete_at: 0,
    object: '',
    role: 'assistant',
    run_id: '',
    status: 'completed',
    thread_id: threadId,
  };

  return [message];
}
