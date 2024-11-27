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
from datetime import datetime

import peewee
from flask_login import current_user
from werkzeug.security import generate_password_hash, check_password_hash

from api.db import UserTenantRole
from api.db.db_models import DB, UserTenant
from api.db.db_models import User, Tenant
from api.db.services.common_service import CommonService
from api.utils import get_uuid, get_format_time, current_timestamp, datetime_format
from api.db import StatusEnum


class UserService(CommonService):
    model = User

    # 获取当前用户
    @classmethod
    @DB.connection_context()
    def get_current_user(cls):
        try:
            if current_user.is_authenticated:
                user = cls.model.select().where(cls.model.id == current_user.id).first()
                if user:
                    user_data = {
                        'id': user.id,
                        'email': user.email,
                        'is_superuser': user.is_superuser
                    }
                    return user_data
                else:
                    return None
            else:
                return None
        except peewee.DoesNotExist:
            return None    

    @classmethod
    @DB.connection_context()
    def filter_by_id(cls, user_id):
        try:
            user = cls.model.select().where(cls.model.id == user_id).get()
            return user
        except peewee.DoesNotExist:
            return None

    @classmethod
    @DB.connection_context()
    def query_user(cls, email, password):
        user = cls.model.select().where((cls.model.email == email),
                                        (cls.model.status == StatusEnum.VALID.value)).first()
        if user:
            print("Stored hashed password:", user.password)
            print("Input password:", password)
        if user and check_password_hash(str(user.password), password):
            return user
        else:
            return None

    @classmethod
    @DB.connection_context()
    def save(cls, **kwargs):
        if "id" not in kwargs:
            kwargs["id"] = get_uuid()
        if "password" in kwargs:
            kwargs["password"] = generate_password_hash(
                str(kwargs["password"]))

        kwargs["create_time"] = current_timestamp()
        kwargs["create_date"] = datetime_format(datetime.now())
        kwargs["update_time"] = current_timestamp()
        kwargs["update_date"] = datetime_format(datetime.now())
        obj = cls.model(**kwargs).save(force_insert=True)
        return obj

    @classmethod
    @DB.connection_context()
    def delete_user(cls, user_ids, update_user_dict):
        with DB.atomic():
            cls.model.update({"status": 0}).where(
                cls.model.id.in_(user_ids)).execute()

    @classmethod
    @DB.connection_context()
    def update_user(cls, user_id, user_dict):
        with DB.atomic():
            if user_dict:
                user_dict["update_time"] = current_timestamp()
                user_dict["update_date"] = datetime_format(datetime.now())
                cls.model.update(user_dict).where(
                    cls.model.id == user_id).execute()
                
    # 获取所有非超级用户
    @classmethod
    @DB.connection_context()
    def list_users(cls):
        try:
            users = cls.model.select().where(cls.model.is_superuser == False)
            return list(users)   
        except Exception as e:
           return []
       
    # 获取管理员
    @classmethod
    @DB.connection_context()
    def get_admin_id(cls):
        try:
            user = cls.model.select().where(cls.model.is_superuser == True).get()
            if user:
                return user.id
            return None
        except Exception as e:
            return None  
    
    # 改变用户状态   
    @classmethod
    @DB.connection_context()
    def change_user_status(cls, user_id, new_status):
        try:
            user = cls.model.select().where(cls.model.id == user_id).get()
            user.status = new_status
            user.save()
            return user
        except Exception as e:
            raise e
        
    # 重置密码
    @classmethod
    @DB.connection_context()
    def reset_password(cls, user_id, new_password):
        try:
            user = cls.model.select().where(cls.model.id == user_id).get()
            hashed_password = generate_password_hash(str(new_password))
            print("New hashed password:", hashed_password)
            user.password = hashed_password
            user.save()
            return user
        except peewee.DoesNotExist:
            return None
        except Exception as e:
            raise e


class TenantService(CommonService):
    model = Tenant

    @classmethod
    @DB.connection_context()
    def get_by_user_id(cls, user_id):
        fields = [
            cls.model.id.alias("tenant_id"),
            cls.model.name,
            cls.model.llm_id,
            cls.model.embd_id,
            cls.model.rerank_id,
            cls.model.asr_id,
            cls.model.img2txt_id,
            cls.model.parser_ids,
            UserTenant.role]
        return list(cls.model.select(*fields)
                    .join(UserTenant, on=((cls.model.id == UserTenant.tenant_id) & (UserTenant.user_id == user_id) & (UserTenant.status == StatusEnum.VALID.value)))
                    .where(cls.model.status == StatusEnum.VALID.value).dicts())

    @classmethod
    @DB.connection_context()
    def get_joined_tenants_by_user_id(cls, user_id):
        fields = [
            cls.model.id.alias("tenant_id"),
            cls.model.name,
            cls.model.llm_id,
            cls.model.embd_id,
            cls.model.asr_id,
            cls.model.img2txt_id,
            UserTenant.role]
        return list(cls.model.select(*fields)
                    .join(UserTenant, on=((cls.model.id == UserTenant.tenant_id) & (UserTenant.user_id == user_id) & (UserTenant.status == StatusEnum.VALID.value) & (UserTenant.role == UserTenantRole.NORMAL.value)))
                    .where(cls.model.status == StatusEnum.VALID.value).dicts())

    @classmethod
    @DB.connection_context()
    def decrease(cls, user_id, num):
        num = cls.model.update(credit=cls.model.credit - num).where(
            cls.model.id == user_id).execute()
        if num == 0:
            raise LookupError("Tenant not found which is supposed to be there")


class UserTenantService(CommonService):
    model = UserTenant

    @classmethod
    @DB.connection_context()
    def save(cls, **kwargs):
        if "id" not in kwargs:
            kwargs["id"] = get_uuid()
        obj = cls.model(**kwargs).save(force_insert=True)
        return obj
