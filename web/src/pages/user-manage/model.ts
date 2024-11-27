import { BaseState } from '@/interfaces/common';
import { IUserInfo, IPermission } from '@/interfaces/database/user-manage';
import { paginationModel } from '@/base';
import { DvaModel } from 'umi';
import { message } from 'antd';
import userManageService from '@/services/userManageService';

export interface UserManageModelState extends BaseState {
    userList: IUserInfo[];
    permissionList: IPermission[];
}

const model: DvaModel<UserManageModelState> = {
    namespace: 'userManage',
    state: {
      userList: [],
      permissionList: [], 
      ...(paginationModel.state as BaseState),
    },
    reducers: {
      setUserList(state, { payload }) {
        return { ...state, userList: payload };
      },
      setPermissionList(state, { payload }) {  // 添加 setPermissionList reducer
        return { ...state, permissionList: payload };
      },
      ...paginationModel.reducers,
    },
    effects: {
      *fetchUserList({ payload = {} }, { call, put, select }) {
        const { searchString, pagination } = yield select(
          (state: any) => state.userManage,
        );
        const { current, pageSize } = pagination;
        const { data } = yield call(userManageService.listUser, {
          ...payload,
          keywords: searchString.trim(),
          page: current,
          pageSize,
        });
        const { retcode, data: res } = data;
        if (retcode === 0 && Array.isArray(res.users)) {
          yield put({
            type: 'setUserList',
            payload: res.users,
          });
          yield put({
            type: 'setPagination',
            payload: { total: res.total },
          });
        }
      },
    //   *createUser({ payload = {} }, { call, put }) {
    //     const { data } = yield call(userManageService.createUser, payload);
    //     if (data.retcode === 0) {
    //       message.success('用户创建成功');
    //       yield put({
    //         type: 'fetchUserList',
    //         payload: {},
    //       });
    //     }
    //     return data.retcode;
    //   },
      // *updateUser({ payload = {} }, { call, put }) {
      //   const { data } = yield call(userManageService.updateUser, payload);
      //   if (data.retcode === 0) {
      //     message.success('用户更新成功');
      //     yield put({
      //       type: 'fetchUserList',
      //       payload: {},
      //     });
      //   }
      //   return data.retcode;
      // },
      // *deleteUser({ payload = {} }, { call, put }) {
      //   const { data } = yield call(userManageService.deleteUser, payload);
      //   if (data.retcode === 0) {
      //     message.success('用户删除成功');
      //     yield put({
      //       type: 'fetchUserList',
      //       payload: {},
      //     });
      //   }
      //   return data.retcode;
      // },
      // *getUserDetail({ payload = {} }, { call }) {
      //   const { data } = yield call(userManageService.getUserDetail, payload);
      //   return data;
      // },
      *changeUserStatus({ payload = {} }, { call, put }) {
        const { data } = yield call(userManageService.changeUserStatus, payload);
        if (data.retcode === 0) {
          message.success('用户状态更新成功');
          yield put({
            type: 'fetchUserList',
            payload: {},
          });
        }
        return data.retcode;
      },
      *get_permission({ payload = {} }, { call, put }) {  // 添加 get_permission 方法
        const { data } = yield call(userManageService.getPermission, payload);
        if (data.retcode === 0 && Array.isArray(data.data)) {
          yield put({
            type: 'setPermissionList',
            payload: data.data,
          });
          message.success('知识库权限列表获取成功');
        } 
        return data.retcode;
      },
    },
  };
  
  export default model;