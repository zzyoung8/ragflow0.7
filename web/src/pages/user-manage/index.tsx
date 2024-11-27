import { Empty, Table, Typography, message } from 'antd';
import { useEffect, useState, useCallback } from 'react';
import { useTranslate } from '@/hooks/commonHooks';
import { useGetUsersPagination, useGetRowSelection, useSelectUserListLoading } from './hooks';
import { ColumnsType } from 'antd/es/table';
import { IUserInfo } from '@/interfaces/database/user-manage';
import { formatDate } from '@/utils/date';
import styles from './index.less';
import UserManagementToolbar from './user-toolbar';
import ActionCell from './action-cell';
import userManageService from '@/services/userManageService'; // 确保导入路径正确

const { Text } = Typography;

const UserManager = () => {
  const { t } = useTranslate('userManage');
  const [userList, setUserList] = useState<IUserInfo[]>([]);
  const [filteredUserList, setFilteredUserList] = useState<IUserInfo[]>([]);
  const { rowSelection, setSelectedRowKeys } = useGetRowSelection();
  const loading = useSelectUserListLoading();
  const { pagination } = useGetUsersPagination();

  const fetchUserList = async () => {
    try {
      const response = await userManageService.listUser({});
      // console.log('API response:', response);     // 添加日志
      if (response.data.retcode === 0) {
        setUserList(response.data.data);
        setFilteredUserList(response.data.data);
      } else {
        message.error(response.retmsg || '获取用户列表失败', 3);
      }
    } catch (error) {
      message.error('获取用户失败', 3);
    }
  };

  useEffect(() => {
    fetchUserList();
  }, []);

  const handleSearch = useCallback((searchString: string) => {
    const filteredData = userList.filter((user) =>
      user.nickname.toLowerCase().includes(searchString.toLowerCase())
    );
    setFilteredUserList(filteredData);
  }, [userList]);

  const columns: ColumnsType<IUserInfo> = [
    {
      title: t('email'),
      dataIndex: 'email',
      key: 'email',
      render(value) {
        return <Text ellipsis={{ tooltip: value }}>{value}</Text>;
      },
    },
    {
      title: t('username'),
      dataIndex: 'nickname',
      key: 'nickname',
      fixed: 'left',
      render(value) {
        return <Text>{value}</Text>;
      },
    },
    {
      title: t('createDate'),
      dataIndex: 'create_time',
      key: 'create_time',
      render(text) {
        return formatDate(text);
      },
    },
    {
      title: t('status'),
      dataIndex: 'status',
      key: 'status',
      render(value) {
        return <Text>{ value=='1'? t('active'): t('disabled') }</Text>;
      },
    },
    {
      title: t('action'),
      dataIndex: 'action',
      key: 'action',
      render: (text, record) => (
        <ActionCell
          record={record}
          fetchUserList={fetchUserList} 
          setSelectedRowKeys={setSelectedRowKeys}
        />
      ),
    },
  ];

  if (!userList.length) {
    return <Empty className={styles.userEmpty}></Empty>;
  }

  return (
    <section className={styles.userManagerWrapper}>
      <UserManagementToolbar
        selectedRowKeys={rowSelection.selectedRowKeys as string[]}
        setSelectedRowKeys={setSelectedRowKeys}
        onSearch={handleSearch}
      />
      <Table
        dataSource={filteredUserList}
        columns={columns}
        rowKey={'id'}
        rowSelection={rowSelection}
        loading={loading}
        pagination={pagination}
        scroll={{ scrollToFirstRowOnChange: true, x: '100%' }}
      />
    </section>
  );
};

export default UserManager;
