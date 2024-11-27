import React, { useState } from 'react';
import { Button, Modal, Table, message, Radio, Form, Input } from 'antd';
import { IUserInfo, IPermission } from '@/interfaces/database/user-manage';
import { ColumnsType } from 'antd/es/table';
import userManageService from '@/services/userManageService';
import { useTranslate } from '@/hooks/commonHooks';
import { useNavigate } from 'umi';
import { KnowledgeRouteKey } from '@/constants/knowledge';
import { rsaPsw } from '@/utils';

interface ActionCellProps {
  record: IUserInfo;
  fetchUserList: () => void;
  setSelectedRowKeys: (keys: React.Key[]) => void;
}

const ActionCell: React.FC<ActionCellProps> = ({ record, fetchUserList, setSelectedRowKeys }) => {
  const { t } = useTranslate('userManage');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isResetPasswordModalVisible, setIsResetPasswordModalVisible] = useState(false);
  const [permissionList, setPermissionList] = useState<IPermission[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleToggleStatus = async () => {
    const newStatus = record.status === '1' ? '0' : '1';
    try {
      const response = await userManageService.changeUserStatus({ userId: record.id, status: newStatus });
      if (response.data.retcode === 0) {
        message.success(`用户已${newStatus === '1' ? '启用' : '禁用'}`);
        fetchUserList();
      } else {
        message.error('操作失败');
      }
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleManagePermissions = async () => {
    try {
      setLoading(true);
      const response = await userManageService.getPermission({ userId: record.id });
      if (response.data.retcode === 0) {
        setPermissionList(response.data.data);
        setIsModalVisible(true);
      } else {
        message.error('获取用户权限列表失败', 3);
      }
    } catch (error) {
      message.error('获取失败', 3);
    } finally {
      setLoading(false);
    }
  };

  const handlePermissionChange = async (userId: string, knowledgebaseId: string, newPermission: any) => {
    try {
      const response = await userManageService.setPermission({ user_id: userId, knowledgebase_id: knowledgebaseId, permission: newPermission });
      if (response.data.retcode === 0) {
        message.success('权限更新成功');
        const updatedList = permissionList.map((item) =>
          item.user_id === userId && item.knowledgebase_id === knowledgebaseId
            ? { ...item, permission: newPermission }
            : item
        );
        setPermissionList(updatedList);
      } else {
        message.error('更新权限失败', 3);
      }
    } catch (error) {
      message.error('更新失败', 3);
    }
  };

  const handleResetPassword = async (values: { newPassword: string }) => {
    try {
      const rsaPassWord = rsaPsw(values.newPassword) as string;
      const response = await userManageService.resetPassword({ userId: record.id, newPassword: rsaPassWord });
      console.log(response);
      if (response.data.retcode === 0) {
        message.success('密码重置成功');
        setIsResetPasswordModalVisible(false);
      } else {
        message.error('密码重置失败');
      }
    } catch (error) {
      message.error('操作失败');
    }
  };



  const handleKnowledgebaseClick = (knowledgebaseId: string) => {
    navigate(`/knowledge/${KnowledgeRouteKey.Dataset}?id=${knowledgebaseId}`, {
      state: { from: 'list' },
    });
  };

  // const shareKnowledge = (knowledgebaseId: string) => {
  //   try{
  //     console.log("知识库id：", knowledgebaseId)
  //     const response = userManageService.shareKnowledge({kb_id: knowledgebaseId})
  //     console.log('response:',response)
  //     if (response.data.retcode === 0){
  //       message.success('共享知识库成功');
  //     } else {
  //       message.error('共享失败')
  //     }
  //   } catch (e){
  //     message.error('出错了')
  //   }
  // };

  const columns: ColumnsType<any> = [
    {
      title: '知识库名称',
      dataIndex: 'knowledgebase_name',
      key: 'knowledgebase_name',
      render: (text, record) => (
        <a onClick={() => handleKnowledgebaseClick(record.knowledgebase_id)}>{text}</a>
      )
    },
    {
      title: '权限',
      dataIndex: 'permission',
      key: 'permission',
      render: (text, record) => (
        <Radio.Group
          value={text}
          onChange={(e) => handlePermissionChange(record.user_id, record.knowledgebase_id, e.target.value)}
        >
          <Radio.Button value="use">无限制</Radio.Button>
          <Radio.Button value="view">仅使用</Radio.Button>
          <Radio.Button value="disabled">禁用</Radio.Button>
        </Radio.Group>
      ),
    },
    // {
    //   title: '共享',
    //   render: (record) => (
    //     <Radio.Button onClick={() => shareKnowledge(record.knowledgebase_id)}>共享</Radio.Button>
    //   )
    // }
  ];

  return (
    <>
      <Button type="link" onClick={handleToggleStatus}>
        {record.status === '1' ? t('deactivation') : t('activation')}
      </Button>
      <Button type="link" onClick={handleManagePermissions}>
        {t('permissions')}
      </Button>
      <Button type='link' onClick={() => setIsResetPasswordModalVisible(true)}>
        {t('ResetPassword')}
      </Button>
      {/* <Button type='link'>
        删除
      </Button> */}
      <Modal
        title={`管理 ${record.nickname} 的权限`}
        visible={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={null}
      >
        <Table
          dataSource={permissionList}
          columns={columns}
          rowKey={'id'}
          pagination={false}
          loading={loading}
        />
      </Modal>
      <Modal
        title="重置密码"
        visible={isResetPasswordModalVisible}
        onCancel={() => setIsResetPasswordModalVisible(false)}
        footer={null}
      >
        <Form onFinish={handleResetPassword}>
          <Form.Item
            name="newPassword"
            label="新密码"
            rules={[{ required: true, message: '请输入新密码' }]}
            style={{ width: '100%' }}
          >
            <Input.Password style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item wrapperCol={{ span: 24, style: { textAlign: 'center' } }}>
            <Button type="primary" htmlType="submit">
              确认
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default ActionCell;
