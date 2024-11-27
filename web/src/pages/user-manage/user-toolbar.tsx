import { useTranslate } from '@/hooks/commonHooks';
import { Input, Space } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useState } from 'react';
import styles from './index.less';

interface IProps {
  selectedRowKeys: string[];
  setSelectedRowKeys: (keys: string[]) => void;
  onSearch: (searchString: string) => void;
}

const UserManagementToolbar = ({
  selectedRowKeys,
  setSelectedRowKeys,
  onSearch,
}: IProps) => {
  const { t } = useTranslate('userManage');
  const [searchString, setSearchString] = useState('');

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchString(value);
    onSearch(value);
  };

  return (
    <div className={styles.filter}>
      <Space>
        <Input
          placeholder={t('searchUsers')}
          value={searchString}
          style={{ width: 220 }}
          allowClear
          onChange={handleInputChange}
          prefix={<SearchOutlined />}
        />
      </Space>
    </div>
  );
};

export default UserManagementToolbar;
