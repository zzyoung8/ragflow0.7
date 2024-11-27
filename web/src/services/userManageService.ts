import api from '@/utils/api';
import registerServer from '@/utils/registerServer';
import request from '@/utils/request';

const {
    listUser,
    changeUserStatus,
    getPermission,
    setPermission,
    checkPermission,
    getAllPermissions,
    resetPassword,
    shareKnowledge,
} = api;
  

const methods = {
    listUser:{
        url: listUser,
        method: 'get',
    },
    changeUserStatus:{
        url: changeUserStatus,
        method: 'post',
    },
    getPermission:{
        url: getPermission,
        method: 'post',
    },
    setPermission:{
        url: setPermission,
        method: 'post',
    },
    checkPermission:{
        url: checkPermission,
        method: 'post',
    },
    getAllPermissions:{
        url: getAllPermissions,
        method: 'post'
    },
    resetPassword:{
        url: resetPassword,
        method: 'post'
    },
    shareKnowledge:{
        url: shareKnowledge,
        method: 'post'
    }
} as const;


const userManagerService = registerServer<keyof typeof methods>(
    methods,
    request,
);
  
export default userManagerService;