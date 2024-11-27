import {
  DatabaseOutlined,
  MergeCellsOutlined,
  RocketOutlined,
  SendOutlined,
  SlidersOutlined,
} from '@ant-design/icons';

export enum Operator {
  Begin = 'Begin',
  Retrieval = 'Retrieval',
  Generate = 'Generate',
  Answer = 'Answer',
  Categorize = 'Categorize',
}

export const operatorIconMap = {
  [Operator.Retrieval]: RocketOutlined,
  [Operator.Generate]: MergeCellsOutlined,
  [Operator.Answer]: SendOutlined,
  [Operator.Begin]: SlidersOutlined,
  [Operator.Categorize]: DatabaseOutlined,
};

export const operatorMap = {
  [Operator.Retrieval]: {
    description: 'Retrieval description drjlftglrthjftl',
  },
  [Operator.Generate]: { description: 'Generate description' },
  [Operator.Answer]: { description: 'Answer description' },
  [Operator.Begin]: { description: 'Begin description' },
  [Operator.Categorize]: { description: 'Categorize description' },
};

export const componentMenuList = [
  {
    name: Operator.Retrieval,
    description: operatorMap[Operator.Retrieval].description,
  },
  {
    name: Operator.Generate,
    description: operatorMap[Operator.Generate].description,
  },
  {
    name: Operator.Answer,
    description: operatorMap[Operator.Answer].description,
  },
  {
    name: Operator.Categorize,
    description: operatorMap[Operator.Categorize].description,
  },
];

export const initialRetrievalValues = {
  similarity_threshold: 0.2,
  keywords_similarity_weight: 0.3,
  top_n: 8,
};

export const initialBeginValues = {
  prologue: `Hi! I'm your assistant, what can I do for you?`,
};

export const initialGenerateValues = {
  // parameters: ModelVariableType.Precise,
  // temperatureEnabled: true,
  temperature: 0.1,
  top_p: 0.3,
  frequency_penalty: 0.7,
  presence_penalty: 0.4,
  max_tokens: 512,
  prompt: `Please summarize the following paragraphs. Be careful with the numbers, do not make things up. Paragraphs as following:
  {cluster_content}
The above is the content you need to summarize.`,
  cite: true,
};

export const initialFormValuesMap = {
  [Operator.Begin]: initialBeginValues,
  [Operator.Retrieval]: initialRetrievalValues,
  [Operator.Generate]: initialGenerateValues,
  [Operator.Answer]: {},
  [Operator.Categorize]: {},
};

export const CategorizeAnchorPointPositions = [
  { top: 1, right: 34 },
  { top: 8, right: 18 },
  { top: 15, right: 10 },
  { top: 24, right: 4 },
  { top: 31, right: 1 },
  { top: 38, right: -2 },
  { top: 62, right: -2 }, //bottom
  { top: 71, right: 1 },
  { top: 79, right: 6 },
  { top: 86, right: 12 },
  { top: 91, right: 20 },
  { top: 98, right: 34 },
];

// key is the source of the edge, value is the target of the edge
// no connection lines are allowed between key and value
export const RestrictedUpstreamMap = {
  [Operator.Begin]: [
    Operator.Begin,
    Operator.Answer,
    Operator.Categorize,
    Operator.Generate,
    Operator.Retrieval,
  ],
  [Operator.Categorize]: [Operator.Begin, Operator.Categorize, Operator.Answer],
  [Operator.Answer]: [],
  [Operator.Retrieval]: [],
  [Operator.Generate]: [],
};

export const NodeMap = {
  [Operator.Begin]: 'beginNode',
  [Operator.Categorize]: 'categorizeNode',
  [Operator.Retrieval]: 'ragNode',
  [Operator.Generate]: 'ragNode',
  [Operator.Answer]: 'ragNode',
};
