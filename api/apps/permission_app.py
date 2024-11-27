from api.db.services.permission_service import PermissionService
from api.db.services.user_service import UserService
from api.utils.api_utils import get_json_result, server_error_response, validate_request
from flask_login import login_required, current_user, login_user, logout_user
from flask import request


# 检索数据库中非root用户并展示 
@manager.route('/list', methods=["GET"])
@login_required
def getUsers():
    try:
        users = UserService.list_users()
        return get_json_result(data=[user.to_dict() for user in users])
    except Exception as e:
        return server_error_response(e)
    
    
# 改变员工状态
# 起始想法：参数应该只有一个就是用户id，然后就是把状态改为对立的那个             
@manager.route('/userStatus', methods=["POST"])
@login_required
def toggle_user_status():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        new_status = data.get('status')
        if not user_id or new_status not in ['0', '1']:
            return get_json_result(data=None, retmsg="Invalid parameters", retcode=400)
        
        user = UserService.change_user_status(user_id, new_status)
        if user:
            return get_json_result(data=user.to_dict())
        else:
            return get_json_result(data=None, retmsg="User not found", retcode=404)
    except Exception as e:
        return server_error_response(e)

        

# 管理用户权限：展示所有知识库(在kb文件，所以接口也在kb)
# 参数：用户id、（多组数据库信息）点击的权限、哪一个知识库
# TODO-修改后对于disabled不能使用该数据库、修改
# TODO-点击后查看相应知识库


# 获得用户知识库权限
@manager.route('/getPermission', methods=['POST'])
@login_required
# @validate_request("user_id")                
def get_permission():
    data = request.json
    user_id = data.get("user_id")
    
    # 获取权限数量
    permission_count = PermissionService.count_permissions()
    print(f"UserKnowledgebasePermission表中的记录数: {permission_count}")
    
    if not user_id:
        return get_json_result(data=None, retmsg="userId is required", retcode=400)
    try:
        perms = PermissionService.list_permission(user_id)
        if perms:
            return get_json_result(data=perms)
        else:
            return get_json_result(data=None, retmsg="Permission not found", retcode=404)
    except Exception as e:
        return server_error_response(e)
    
    
# 设置用户知识库权限
@manager.route('/setPermission', methods=['POST'])
@login_required
def set_permission():
    req = request.json
    # print(req)
    user_id = req.get('user_id')
    knowledgebase_id = req.get('knowledgebase_id')
    permission = req.get('permission')

    if not user_id or not knowledgebase_id or not permission:
        return get_json_result(data=None, retmsg="参数不完整", retcode=404)
    try:
        perm = PermissionService.set_permission(user_id, knowledgebase_id, permission)
        return get_json_result(data=perm)
    except Exception as e:
        return server_error_response(e)

# 检查知识库权限
@manager.route('/checkPermission', methods=['POST'])
@login_required
def check_permission():
    data = request.json
    # print(data)
    user_id = data.get("user_id")
    knowledge_id = data.get("knowledge_id")
    
    if not user_id or not knowledge_id:
        return get_json_result(data=None, retmsg="userId and knowledgeId are required", retcode=400)
    
    try:
        permission = PermissionService.get_permission(user_id, knowledge_id)
        if permission:
            return get_json_result(data=permission)
        else:
            return get_json_result(data=None, retmsg="Permission not found", retcode=404)
    except Exception as e:
        return server_error_response(e)

# 获取某用户所有权限
@manager.route('/getAllPermissions', methods=['POST'])
@login_required
def get_all_permissions():
    data = request.json
    user_id = data.get("user_id")
    
    if not user_id:
        return get_json_result(data=None, retmsg="userId is required", retcode=400)
    
    try:
        permissions = PermissionService.list_all_permissions(user_id)
        if permissions:
            return get_json_result(data=permissions)
        else:
            return get_json_result(data=None, retmsg="Permissions not found", retcode=404)
    except Exception as e:
        return server_error_response(e)
    
# 删除知识库权限
@manager.route('/deletePermission', methods=['POST'])
@login_required
def delete_permission():
    data = request.json
    # print(data)
    kb_id = data.get('kb_id')
    
    if not kb_id:
        return get_json_result(data=None, retmsg="knowledge_id is required", retcode=400)
    try:
        result = PermissionService.delete_permission(kb_id)
        if result > 0: 
            return get_json_result(data=None, retmsg="Permission deleted successfully")
        else:
            return get_json_result(data=None, retmsg="Permission not found", retcode=404)
    except ValueError as e:
        return get_json_result(data=None, retmsg=str(e), retcode=404)
    except Exception as e:
        return get_json_result(data=None, retmsg=f"An error occurred: {str(e)}", retcode=500)