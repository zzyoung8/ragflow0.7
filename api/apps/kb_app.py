#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
from elasticsearch_dsl import Q
from flask import request
from flask_login import login_required, current_user

from api.db.services import duplicate_name
from api.db.services.document_service import DocumentService
from api.db.services.file2document_service import File2DocumentService
from api.db.services.file_service import FileService
from api.db.services.user_service import TenantService, UserTenantService
from api.utils.api_utils import server_error_response, get_data_error_result, validate_request
from api.utils import get_uuid, get_format_time
from api.db import StatusEnum, UserTenantRole, FileSource
from api.db.services.user_service import UserService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.permission_service import PermissionService
from api.db.db_models import Knowledgebase, File
from api.settings import stat_logger, RetCode
from api.utils.api_utils import get_json_result
from rag.nlp import search
from rag.utils.es_conn import ELASTICSEARCH


@manager.route('/create', methods=['post'])
@login_required
@validate_request("name")
def create():
    req = request.json
    req["name"] = req["name"].strip()
    req["name"] = duplicate_name(
        KnowledgebaseService.query,
        name=req["name"],
        tenant_id=current_user.id,
        status=StatusEnum.VALID.value)
    try:
        req["id"] = get_uuid()
        req["tenant_id"] = current_user.id
        req["created_by"] = current_user.id
        e, t = TenantService.get_by_id(current_user.id)
        if not e:
            return get_data_error_result(retmsg="Tenant not found.")
        req["embd_id"] = t.embd_id
        
        permission_data = {
            "id": get_uuid(),
            "user_id": current_user.id,
            "nickname": current_user.nickname,  # 假设有
            "email": current_user.email,        # 假设有
            "knowledgebase_id": req["id"],
            "knowledgebase_name": req["name"],
            "permission": "use"    # 默认为use
        }
        if not PermissionService.save(**permission_data):
            return get_data_error_result(retmsg="Failed to save user permission")
        
        # 查询用户是否为超级管理员
        user = UserService.get_current_user()
        # 确保 user 字典中有 is_superuser 键
        if user and 'is_superuser' in user:
            req["is_shared"] = int(user['is_superuser'])  # 将布尔值转换为整数
            
            # 若是管理员创建的知识库，保存管理员权限信息同时向所有用户权限表插入view数据
            if user['is_superuser'] == True:
                # 查询所有非管理员，然后向其中插入权限数据
                users = UserService.list_users()
                
                for user in users:
                    user_dict = user.to_dict()
                    permission_data = {
                        "id": get_uuid(),
                        "user_id": user_dict['id'],
                        "nickname": user_dict['nickname'],  # 假设有
                        "email": user_dict['email'],        # 假设有
                        "knowledgebase_id": req["id"],
                        "knowledgebase_name": req["name"],
                        "permission": "view"    # 只能用
                    }
                    if not PermissionService.save(**permission_data):
                        return get_data_error_result(retmsg="Failed to save user permission")
        else:
            req["is_shared"] = 0
            
        # 保存信息
        if not KnowledgebaseService.save(**req):
            return get_data_error_result()
        
        # if not PermissionService.save(**permission_data):
        #     return get_data_error_result(retmsg="Failed to save user permission")
        
        return get_json_result(data={"kb_id": req["id"]})
    except Exception as e:
        return server_error_response(e)


@manager.route('/update', methods=['post'])
@login_required
@validate_request("kb_id", "name", "description", "permission", "parser_id")
def update():
    req = request.json
    req["name"] = req["name"].strip()
    try:
        if not KnowledgebaseService.query(
                created_by=current_user.id, id=req["kb_id"]):
            return get_json_result(
                data=False, retmsg=f'Only owner of knowledgebase authorized for this operation.', retcode=RetCode.OPERATING_ERROR)

        e, kb = KnowledgebaseService.get_by_id(req["kb_id"])
        if not e:
            return get_data_error_result(
                retmsg="Can't find this knowledgebase!")

        if req["name"].lower() != kb.name.lower() \
                and len(KnowledgebaseService.query(name=req["name"], tenant_id=current_user.id, status=StatusEnum.VALID.value)) > 1:
            return get_data_error_result(
                retmsg="Duplicated knowledgebase name.")

        del req["kb_id"]
        if not KnowledgebaseService.update_by_id(kb.id, req):
            return get_data_error_result()

        e, kb = KnowledgebaseService.get_by_id(kb.id)
        if not e:
            return get_data_error_result(
                retmsg="Database error (Knowledgebase rename)!")

        return get_json_result(data=kb.to_json())
    except Exception as e:
        return server_error_response(e)


@manager.route('/detail', methods=['GET'])
@login_required
def detail():
    kb_id = request.args["kb_id"]
    try:
        kb = KnowledgebaseService.get_detail(kb_id)
        if not kb:
            return get_data_error_result(
                retmsg="Can't find this knowledgebase!")
        return get_json_result(data=kb)
    except Exception as e:
        return server_error_response(e)

# 获取是否共享
@manager.route('/getShared', methods=['POST'])
@login_required
def get_is_shared():
    kb_id = request.json.get("kb_id")
    try:
        is_or_not = KnowledgebaseService.is_shared(kb_id)
        if not is_or_not:
            return get_data_error_result(retmsg="can not get whether is shared or not")
        return get_json_result(data = is_or_not)
    except Exception as e:
        return server_error_response(e)
   
# 改变共享状态     
@manager.route('/changeShare', methods=['POST'])
@login_required
def changeShare():
    data = request.json
    kb_id = data.get("kb_id")
    is_shared = data.get("checked")
    
    print(data)
    if kb_id is None or is_shared is None:
        return get_data_error_result(retmsg="Missing kb_id or is_shared parameter")
    try:
        is_shared = int(is_shared)
        is_success = KnowledgebaseService.change_share(kb_id, is_shared)
        if is_success:
            return get_json_result(data={"success": True})
        else:
            return get_json_result(data={"success": False, "msg": "Failed to update share status"})
    except Exception as e:
        return server_error_response(e)



@manager.route('/list', methods=['GET'])
@login_required
def list_kbs():
    page_number = request.args.get("page", 1)
    items_per_page = request.args.get("page_size", 150)
    orderby = request.args.get("orderby", "create_time")
    desc = request.args.get("desc", True)
    try:
        tenants = TenantService.get_joined_tenants_by_user_id(current_user.id)
        kbs = KnowledgebaseService.get_by_tenant_ids(
            [m["tenant_id"] for m in tenants], current_user.id, page_number, items_per_page, orderby, desc)
        return get_json_result(data=kbs)
    except Exception as e:
        return server_error_response(e)


@manager.route('/rm', methods=['post'])
@login_required
@validate_request("kb_id")
def rm():
    req = request.json
    try:
        kbs = KnowledgebaseService.query(
                created_by=current_user.id, id=req["kb_id"])
        if not kbs:
            return get_json_result(
                data=False, retmsg=f'Only owner of knowledgebase authorized for this operation.', retcode=RetCode.OPERATING_ERROR)

        for doc in DocumentService.query(kb_id=req["kb_id"]):
            if not DocumentService.remove_document(doc, kbs[0].tenant_id):
                return get_data_error_result(
                    retmsg="Database error (Document removal)!")
            f2d = File2DocumentService.get_by_document_id(doc.id)
            FileService.filter_delete([File.source_type == FileSource.KNOWLEDGEBASE, File.id == f2d[0].file_id])
            File2DocumentService.delete_by_document_id(doc.id)

        if not KnowledgebaseService.delete_by_id(req["kb_id"]):
            return get_data_error_result(
                retmsg="Database error (Knowledgebase removal)!")
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)
