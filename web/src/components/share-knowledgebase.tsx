import { useTranslate } from "@/hooks/commonHooks";
import { useKnowledgeBaseId } from "@/hooks/knowledgeHook";
import kbService from "@/services/kbService";
import userService from "@/services/userService";
import { Form, message, Switch } from "antd";
import { useEffect, useState } from "react";

const ShareKnowledgebase = () => {
    const { t } = useTranslate('knowledgeDetails');

    const [currentUser, setCurrentUser] = useState<{ is_superuser: boolean } | null>(null);
    const [isShared, setIsShared] = useState<boolean>(false); // 将初始值设置为 false
    const [loading, setLoading] = useState<boolean>(true);

    const kb_id = useKnowledgeBaseId();

    // 获取当前用户的功能
    useEffect(() => {
        const fetchCurrentUser = async () => {
            try {
                const response = await userService.current_user();
                if (response.data.retcode === 0) {
                    setCurrentUser(response.data.data);
                } else {
                    console.error('获取当前用户失败');
                }
            } catch (error) {
                console.error('获取当前用户时出错:', error);
            }
        };

        fetchCurrentUser();
    }, []);

    // 获取当前知识库共享状态
    useEffect(() => {
        const fetchKnowledgebaseShared = async () => {
            if (!kb_id) {
                return; // 直接返回，避免发送错误的请求
            }
            try {
                const response = await kbService.getShared({kb_id: kb_id});
                console.log("API 响应:", response.data);
                if (response.data.retcode === 0) {
                    setIsShared(response.data.data === 1); // 设置共享状态
                } else {
                    console.error('获取知识库详情失败');
                }
            } catch (error) {
                console.error('获取知识库详情时出错:', error);
            } finally {
                setLoading(false); // 数据加载完成
            }
        };
        fetchKnowledgebaseShared();
    }, [kb_id]);

    // 打印 isShared 的值以调试
    useEffect(() => {
        console.log("当前 isShared 值:", isShared);
    }, [isShared]);

    // 修改共享状态
    const handleSwitchChange = async (checked: boolean) => {
        try {
            const response = await kbService.changeShare({kb_id: kb_id, checked: checked ? '1' : '0'});
            if (response.data.retcode === 0) {
                setIsShared(checked);
            } else {
                message.error("更新共享状态失败");
            }
        } catch (error) {
            message.error("更新共享状态时出错: " + error);
        }
    };

    // 如果当前用户信息还未加载，显示加载中
    if (!currentUser) {
        return <div>加载中...</div>;
    }

    // 如果当前用户不是管理员，则不显示该组件
    if (!currentUser.is_superuser) {
        return null;
    }

    // 管理员才能看到共享开关
    return (
        <Form.Item
            name={['parser_config', 'share_knowledgebase']}
            label={t('shareKnowledgebase')}
            valuePropName="checked"
            tooltip={t('shareKnowledgebaseTip')}
        >
            <Switch
                checked={isShared}
                onChange={handleSwitchChange}
                loading={loading}
                // disabled={loading} // 在加载时禁用开关
            />
        </Form.Item>
    );
};

export default ShareKnowledgebase;
