import { useTranslate } from '@/hooks/commonHooks';
import { useFetchKnowledgeList } from '@/hooks/knowledgeHook';
import { Form, Select, message } from 'antd';
import { useEffect, useState } from 'react';
import { IKnowledge } from '@/interfaces/database/knowledge';
import { IPermission } from '@/interfaces/database/user-manage';
import { useSelectUserInfo } from '@/hooks/userSettingHook';
import userManagerService from '@/services/userManageService';

const KnowledgeBaseItem = () => {
  const { t } = useTranslate('chat');
  const { list: knowledgeList, loading } = useFetchKnowledgeList(true);
  const [filteredKnowledgeList, setFilteredKnowledgeList] = useState<IKnowledge[]>([]);
  const userInfo = useSelectUserInfo();

  useEffect(() => {
    const fetchPermissions = async () => {
      try {
        const response = await userManagerService.getAllPermissions({
          user_id: userInfo.id,
        });
        if (response.data.retcode === 0) {
          const permissions: IPermission[] = response.data.data;
          const filteredList = knowledgeList.filter((kb) => {
            const kbPermission = permissions.find(
              (perm) => perm.knowledgebase_id === kb.id
            );
            return kbPermission && kbPermission.permission !== 'disabled';
          });
          setFilteredKnowledgeList(filteredList);
        } else {
          message.error(t('fetchPermissionsError'));
        }
      } catch (error) {
        message.error(t('fetchPermissionsError'));
      }
    };

    if (knowledgeList.length > 0) {
      fetchPermissions();
    }
  }, [knowledgeList, userInfo.id, t]);

  const knowledgeOptions = filteredKnowledgeList.map((x) => ({
    label: x.name,
    value: x.id,
  }));

  return (
    <Form.Item
      label={t('knowledgeBases')}
      name="kb_ids"
      tooltip={t('knowledgeBasesTip')}
      rules={[
        {
          required: true,
          message: t('knowledgeBasesMessage'),
          type: 'array',
        },
      ]}
    >
      <Select
        mode="multiple"
        options={knowledgeOptions}
        placeholder={t('knowledgeBasesMessage')}
        loading={loading}
      ></Select>
    </Form.Item>
  );
};

export default KnowledgeBaseItem;
