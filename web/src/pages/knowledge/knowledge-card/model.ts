// import { Effect, Reducer } from 'umi';
// import userManagerService from '@/services/userManageService';
// import { IPermission } from '@/interfaces/database/user-manage';

// export interface PermissionModelState {
//   permissionInfo: IPermission[];
// }

// export interface PermissionModelType {
//   namespace: 'permissionModel';
//   state: PermissionModelState;
//   effects: {
//     getPermissionInfo: Effect;
//   };
//   reducers: {
//     savePermissionInfo: Reducer<PermissionModelState>;
//   };
// }

// const PermissionModel: PermissionModelType = {
//   namespace: 'permissionModel',
//   state: {
//     permissionInfo: {} as IPermission[],
//   },
//   effects: {
//     *getPermissionInfo(_, { call, put }): Generator<any, void, any> {
//       const response = yield call(userManagerService.getPermission);
//       console.log("响应为：", response);
//       yield put({
//         type: 'savePermissionInfo',
//         payload: response.data.data,
//       });
//     },
//   },
//   reducers: {
//     savePermissionInfo(state, action) {
//       return {
//         ...state,
//         permissionInfo: action.payload,
//       };
//     },
//   },
// };

// export default PermissionModel;
