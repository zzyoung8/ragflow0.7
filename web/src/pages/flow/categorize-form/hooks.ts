import get from 'lodash/get';
import omit from 'lodash/omit';
import { useCallback, useEffect } from 'react';
import { Edge, Node } from 'reactflow';
import { Operator } from '../constant';
import {
  ICategorizeItem,
  ICategorizeItemResult,
  IOperatorForm,
  NodeData,
} from '../interface';
import useGraphStore from '../store';

// exclude some nodes downstream of the classification node
const excludedNodes = [Operator.Categorize, Operator.Answer, Operator.Begin];

export const useBuildCategorizeToOptions = () => {
  const nodes = useGraphStore((state) => state.nodes);

  return nodes
    .filter((x) => excludedNodes.every((y) => y !== x.data.label))
    .map((x) => ({ label: x.id, value: x.id }));
};

/**
   * convert the following object into a list
   * 
   * {
      "product_related": {
      "description": "The question is about product usage, appearance and how it works.",
      "examples": "Why it always beaming?\nHow to install it onto the wall?\nIt leaks, what to do?",
      "to": "generate:0"
      }
      }
*/
const buildCategorizeListFromObject = (
  categorizeItem: ICategorizeItemResult,
  edges: Edge[],
  node?: Node<NodeData>,
) => {
  // Categorize's to field has two data sources, with edges as the data source.
  // Changes in the edge or to field need to be synchronized to the form field.
  return Object.keys(categorizeItem).reduce<Array<ICategorizeItem>>(
    (pre, cur) => {
      // synchronize edge data to the to field
      const edge = edges.find(
        (x) => x.source === node?.id && x.sourceHandle === cur,
      );
      pre.push({ name: cur, ...categorizeItem[cur], to: edge?.target });
      return pre;
    },
    [],
  );
};

/**
   * Convert the list in the following form into an object
   * {
    "items": [
      {
        "name": "Categorize 1",
        "description": "111",
        "examples": "ddd",
        "to": "Retrieval:LazyEelsStick"
      }
     ]
    }
*/
const buildCategorizeObjectFromList = (list: Array<ICategorizeItem>) => {
  return list.reduce<ICategorizeItemResult>((pre, cur) => {
    if (cur?.name) {
      pre[cur.name] = omit(cur, 'name');
    }
    return pre;
  }, {});
};

export const useHandleFormValuesChange = ({
  onValuesChange,
  form,
  node,
}: IOperatorForm) => {
  const edges = useGraphStore((state) => state.edges);

  const handleValuesChange = useCallback(
    (changedValues: any, values: any) => {
      console.info(changedValues, values);
      onValuesChange?.(changedValues, {
        ...omit(values, 'items'),
        category_description: buildCategorizeObjectFromList(values.items),
      });
    },
    [onValuesChange],
  );

  useEffect(() => {
    form?.setFieldsValue({
      items: buildCategorizeListFromObject(
        get(node, 'data.form.category_description', {}),
        edges,
        node,
      ),
    });
  }, [form, node, edges]);

  return { handleValuesChange };
};

export const useHandleToSelectChange = (nodeId?: string) => {
  const { addEdge } = useGraphStore((state) => state);
  const handleSelectChange = useCallback(
    (name?: string) => (value?: string) => {
      if (nodeId && value && name) {
        addEdge({
          source: nodeId,
          target: value,
          sourceHandle: name,
          targetHandle: null,
        });
      }
    },
    [addEdge, nodeId],
  );

  return { handleSelectChange };
};
