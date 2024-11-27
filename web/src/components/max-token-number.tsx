import { useTranslate } from '@/hooks/commonHooks';
import { Flex, Form, InputNumber, Slider } from 'antd';

const MaxTokenNumber = () => {
  const { t } = useTranslate('knowledgeConfiguration');

  return (
    <div>
    <Form.Item label={t('chunkTokenNumber')} tooltip={t('chunkTokenNumberTip')}>
      <Flex gap={20} align="center">
        <Flex flex={1}>
          <Form.Item
            name={['parser_config', 'chunk_token_num']}
            noStyle
            initialValue={128}
            rules={[{ required: true, message: t('chunkTokenNumberMessage') }]}
          >
            <Slider max={2048} style={{ width: '100%' }} />
          </Form.Item>
        </Flex>
        <Form.Item
          name={['parser_config', 'chunk_token_num']}
          noStyle
          rules={[{ required: true, message: t('chunkTokenNumberMessage') }]}
        >
          <InputNumber max={2048} min={0} />
        </Form.Item>
      </Flex>
    </Form.Item>
       
    {/* 加一个chunk_overlap */}
    <Form.Item label={t('chunkOverlap')} tooltip={t('chunkOverlapTip')}>
      <Flex gap={20} align="center">
        <Flex flex={1}>
          <Form.Item
            name={['parser_config', 'chunk_overlap']}
            noStyle
            initialValue={0.5} // 设置初始值在0到1之间
            rules={[{ required: true, message: t('chunkOverlapMessage') }]}
          >
            <Slider
              max={1}
              min={0}
              step={0.01} // 设置步长为0.01，以便更精细地控制
              style={{ width: '100%' }}
            />
          </Form.Item>
        </Flex>
        <Form.Item
          name={['parser_config', 'chunk_overlap']}
          noStyle
          rules={[{ required: true, message: t('chunkOverlapMessage') }]}
        >
          <InputNumber
            min={0}
            max={1}
            step={0.01} // 设置步长为0.01，以便更精细地控制
            style={{ width: 80 }}
          />
        </Form.Item>
      </Flex>
    </Form.Item>
  </div>
  );
};

export default MaxTokenNumber;
