// 用户信息
export interface IUserInfo {
    access_token: string;
    avatar?: any;
    color_schema: string;
    create_date: string;
    create_time: number;
    email: string;
    id: string;
    is_active: string;
    is_anonymous: string;
    is_authenticated: string;
    is_superuser: boolean;
    language: string;
    last_login_time: string;
    login_channel: string;
    nickname: string;
    password: string;
    status: string;
    update_date: string;
    update_time: number;
  }
  
export interface IPermission {
  id: string;
  user_id: string;
  nickname: string;
  email: string;
  knowledgebase_id: string;
  knowledgebase_name: string;
  permission: string
}