import { IUserInfo } from "@/interfaces/database/user-manage";
import { TableRowSelection } from "antd/es/table/interface";
import { useOneNamespaceEffectsLoading } from '@/hooks/storeHooks';
import { useCallback, useState } from "react";
import { useDispatch, useSelector } from "umi";
import { useGetPagination, useSetPagination } from "@/hooks/logicHooks";
import { PaginationProps } from "antd";

// 关于表格行的相关操作
export const useGetRowSelection = () => {
    const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  
    const rowSelection: TableRowSelection<IUserInfo> = {
      selectedRowKeys,
    //   getCheckboxProps: (record) => {
    //     return { disabled: record.source_type === 'knowledgebase' };
    //   },
      onChange: (newSelectedRowKeys: React.Key[]) => {
        setSelectedRowKeys(newSelectedRowKeys);
      },
    };
  
    return { rowSelection, setSelectedRowKeys };
};

// 加载用户列表
export const useSelectUserListLoading = () => {
    return useOneNamespaceEffectsLoading('userManage', ['userFile']);
};

// 用户分页
export const useGetUsersPagination = () => {
    const { pagination } = useSelector((state) => state.userManage);
  
    const setPagination = useSetPagination('userManage');
  
    const onPageChange: PaginationProps['onChange'] = useCallback(
      (pageNumber: number, pageSize: number) => {
        setPagination(pageNumber, pageSize);
      },
      [setPagination],
    );
  
    const { pagination: paginationInfo } = useGetPagination(
      pagination.total,
      pagination.current,
      pagination.pageSize,
      onPageChange,
    );
  
    return {
      pagination: paginationInfo,
      setPagination,
    };
};


export const useHandleSearchChange = () => {
  const dispatch = useDispatch();
  const { searchString } = useSelector((state) => state.fileManager);
  const setPagination = useSetPagination('fileManager');

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const value = e.target.value;
      dispatch({ type: 'fileManager/setSearchString', payload: value });
      setPagination();
    },
    [setPagination, dispatch],
  );

  return { handleInputChange, searchString };
};