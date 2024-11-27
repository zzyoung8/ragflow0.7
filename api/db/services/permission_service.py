from api.db.db_models import DB, User, UserKnowledgebasePermission
from api.db.services.common_service import CommonService
from api.db.services.knowledgebase_service import KnowledgebaseService

class PermissionService(CommonService):
    model = UserKnowledgebasePermission
            
    # 获取用户知识库权限
    @classmethod
    @DB.connection_context()
    def list_permission(cls, user_id):
        try:
            perms = (cls.model
                    .select(cls.model.user_id, cls.model.knowledgebase_id, cls.model.knowledgebase_name, cls.model.permission)
                    .where(cls.model.user_id == user_id)
                    .dicts())
            return list(perms)
        except Exception as e:
            raise e
        
        
    # 设置用户知识库权限
    @classmethod
    @DB.connection_context()
    def set_permission(cls, user_id, knowledgebase_id, permission):
        try:
            # 查找或创建权限记录
            perm, created = cls.model.get_or_create(
                user_id=user_id, 
                knowledgebase_id=knowledgebase_id,
                defaults={'permission': permission})
            # 更新权限
            if not created:
                perm.permission = permission
                perm.save()
                
            perm_dict = {
                "user_id": perm.user_id,
                "knowledgebase_id": perm.knowledgebase_id,
                "knowledgebase_name": perm.knowledgebase_name,
                "permission": perm.permission
            }
            return perm_dict
        except Exception as e:
            raise e


    # 查找用户权限数据库数据数量
    @classmethod
    @DB.connection_context()
    def count_permissions(cls):
        try:
            count = cls.model.select().count()
            return count
        except Exception as e:
            raise e
        
    # 检查知识库权限
    @classmethod
    @DB.connection_context()
    def get_permission(cls, user_id, knowledge_id):
        try:
            # 这是根据用户id查询的知识库权限
            perm = (cls.model
                    .select(cls.model.permission)
                    .where(cls.model.user_id == user_id, cls.model.knowledgebase_id == knowledge_id)
                    .first()
                    )
            
            if perm:
                return {"permission": perm.permission}
            else:
                # 根据用户id(该用户非创建者)和数据库id查询是否为共享数据库
                shared = KnowledgebaseService.is_shared(knowledge_id)
                # print(shared)
                # 是的话就根据这个知识库id返回权限表里的权限use
                if shared == 1:
                    perm = (cls.model
                                .select(cls.model.permission)
                                .where(cls.model.knowledgebase_id == knowledge_id)
                                .first()
                    )
                    return {"permission": perm.permission} if perm else None
                else:
                    return None
        except Exception as e:
            raise e 
        
    # 获得某用户的所有权限    
    @classmethod
    @DB.connection_context()
    def list_all_permissions(cls, user_id):
        try:
            perms = (cls.model
                     .select()
                     .where(cls.model.user_id == user_id))
            return [{"knowledgebase_id": perm.knowledgebase_id, "permission": perm.permission} for perm in perms]
        except Exception as e:
            raise e
        
    # 删除权限
    @classmethod
    @DB.connection_context()
    def delete_permission(cls, kb_id):
        try:
            result = cls.model.delete().where(cls.model.knowledgebase_id == kb_id).execute()   
            return result 
        except peewee.DoesNotExist:
            raise ValueError("Permission not found")
        except Exception as e:
            raise e
            

    
    