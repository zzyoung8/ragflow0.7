import { ReactComponent as StarIon } from '@/assets/svg/chat-star.svg';
import { ReactComponent as FileIcon } from '@/assets/svg/file-management.svg';
import { ReactComponent as KnowledgeBaseIcon } from '@/assets/svg/knowledge-base.svg';
import { ReactComponent as PermissionBaseIcon } from '@/assets/svg/use-management.svg';
import { useTranslate } from '@/hooks/commonHooks';
import { useNavigateWithFromState } from '@/hooks/routeHook';
import { Layout, Radio, Space, theme } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation } from 'umi';
import Toolbar from '../right-toolbar';
import userService from '@/services/userService';

import { useFetchAppConf } from '@/hooks/logicHooks';
import styles from './index.less';

const { Header } = Layout;

const RagHeader = () => {
  const {
    token: { colorBgContainer },
  } = theme.useToken();
  const navigate = useNavigateWithFromState();
  const { pathname } = useLocation();
  const { t } = useTranslate('header');
  const appConf = useFetchAppConf();

  const tagsData = useMemo(
    () => [
      { path: '/knowledge', name: t('knowledgeBase'), icon: KnowledgeBaseIcon },
      { path: '/chat', name: t('chat'), icon: StarIon },
      { path: '/file', name: t('fileManager'), icon: FileIcon },
      { path: '/permission', name: t('userManage'), icon: PermissionBaseIcon },
    ],
    [t],
  );

  const currentPath = useMemo(() => {
    return (
      tagsData.find((x) => pathname.startsWith(x.path))?.name || 'knowledge'
    );
  }, [pathname, tagsData]);

  const handleChange = (path: string) => {
    navigate(path);
  };

  const handleLogoClick = useCallback(() => {
    navigate('/');
  }, [navigate]);

  // 加的内容
  const [currentUser, setCurrentUser] = useState<{ is_superuser: boolean } | null>(null);

  
  useEffect(() => {
    // 在组件加载时获取当前用户信息
    const fetchCurrentUser = async () => {
      try {
        const response = await userService.current_user()
        // console.log("当前用户的response:", response)
        if (response.data.retcode == 0) {
          // const userData = await response.json();
          setCurrentUser(response.data.data);
        } else {
          // 处理请求失败的情况
          console.error('Failed to fetch current user');
        }
      } catch (error) {
        console.error('Error fetching current user:', error);
      }
    };

    fetchCurrentUser();
  }, []);

  if (!currentUser) {
    // 如果当前用户信息还在加载中，可以显示加载动画或其他提示
    return <div>Loading...</div>;
  }

  const isSuperuser = currentUser.is_superuser;
  // console.log("当前用户是否为superuser:", isSuperuser)
  // 这里一个图片一个文字，修改为一个图片即可
  return (
    <Header
      style={{
        padding: '0 16px',
        background: colorBgContainer,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        height: '72px',
      }}
    >
      <Space size={12} onClick={handleLogoClick} className={styles.logoWrapper}>
        <img src="/saic-gm.png" alt="" className={styles.appIcon} />
        {/* <span className={styles.appName}>{appConf.appName}</span> */}
      </Space>
      <Space size={[0, 8]} wrap>
        <Radio.Group
          defaultValue="a"
          buttonStyle="solid"
          className={styles.radioGroup}
          value={currentPath}
        >
          {tagsData.map((item) => 
          // 加的一行,判断是否为管理员，是的话才渲染 '/permission'
          !(item.path === '/permission' && !isSuperuser) &&(
            <Radio.Button
              value={item.name}
              onClick={() => handleChange(item.path)}
              key={item.name}
            >
              <Space>
                <item.icon
                  className={styles.radioButtonIcon}
                  stroke={item.name === currentPath ? 'black' : 'white'}
                ></item.icon>
                {item.name}
              </Space>
            </Radio.Button>
          ))}
        </Radio.Group>
      </Space>
      <Toolbar></Toolbar>
    </Header>
  );
};

export default RagHeader;
