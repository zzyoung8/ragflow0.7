// import { useDispatch, useSelector } from 'umi';
// import { useCallback, useEffect } from 'react';
// import { IPermission } from '@/interfaces/database/user-manage';

// export const useFetchPermissionInfo = () => {
//   const dispatch = useDispatch();

//   const fetchPermissionInfo = useCallback(() => {
//     dispatch({ type: 'permissionModel/getPermissionInfo' });
//   }, [dispatch]);

//   useEffect(() => {
//     fetchPermissionInfo();
//   }, [fetchPermissionInfo]);

//   return fetchPermissionInfo;
// };

// export const useSelectPermissionInfo = (): IPermission[] => {
//   const permissionInfo: IPermission[] = useSelector(
//     (state: any) => state.permissionModel.permissionInfo,
//   );

//   return permissionInfo;
// };
