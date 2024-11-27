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
import re
from copy import deepcopy

from api.db import LLMType
from api.db.db_models import Dialog, Conversation
from api.db.services.common_service import CommonService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.llm_service import LLMService, TenantLLMService, LLMBundle
from api.settings import chat_logger, retrievaler
from rag.app.resume import forbidden_select_fields4resume
from rag.nlp.rag_tokenizer import is_chinese
from rag.nlp.search import index_name
from rag.utils import rmSpace, num_tokens_from_string, encoder


class DialogService(CommonService):
    model = Dialog


class ConversationService(CommonService):
    model = Conversation


def message_fit_in(msg, max_length=4000):
    def count():
        nonlocal msg
        tks_cnts = []
        for m in msg:
            tks_cnts.append(
                {"role": m["role"], "count": num_tokens_from_string(m["content"])})
        total = 0
        for m in tks_cnts:
            total += m["count"]
        return total

    c = count()
    if c < max_length:
        return c, msg

    msg_ = [m for m in msg[:-1] if m["role"] == "system"]
    msg_.append(msg[-1])
    msg = msg_
    c = count()
    if c < max_length:
        return c, msg

    ll = num_tokens_from_string(msg_[0]["content"])
    l = num_tokens_from_string(msg_[-1]["content"])
    if ll / (ll + l) > 0.8:
        m = msg_[0]["content"]
        m = encoder.decode(encoder.encode(m)[:max_length - l])
        msg[0]["content"] = m
        return max_length, msg

    m = msg_[1]["content"]
    m = encoder.decode(encoder.encode(m)[:max_length - l])
    msg[1]["content"] = m
    return max_length, msg


def chat(dialog, messages, stream=True, **kwargs):
    assert messages[-1]["role"] == "user", "The last content of this conversation is not from user."
    # 获取LLM配置
    llm = LLMService.query(llm_name=dialog.llm_id)
    if not llm:
        # 获取租户LLM配置
        llm = TenantLLMService.query(tenant_id=dialog.tenant_id, llm_name=dialog.llm_id)
        if not llm:
            raise LookupError("LLM(%s) not found" % dialog.llm_id)
        max_tokens = 1024
    else:
        max_tokens = llm[0].max_tokens
    # print("dialog.kb_ids:", dialog.kb_ids)
    kbs = KnowledgebaseService.get_by_ids(dialog.kb_ids)
    # print("Retrieved knowledge bases:", kbs)
    embd_nms = list(set([kb.embd_id for kb in kbs]))
    if len(embd_nms) != 1:
        yield {"answer": "**ERROR**: Knowledge bases use different embedding models.", "reference": []}
        return {"answer": "**ERROR**: Knowledge bases use different embedding models.", "reference": []}
    # 获取问题，获取嵌入模型，获取聊天模型
    questions = [m["content"] for m in messages if m["role"] == "user"]
    embd_mdl = LLMBundle(dialog.tenant_id, LLMType.EMBEDDING, embd_nms[0])
    chat_mdl = LLMBundle(dialog.tenant_id, LLMType.CHAT, dialog.llm_id)
    # 获取提示词配置
    prompt_config = dialog.prompt_config
    field_map = KnowledgebaseService.get_field_map(dialog.kb_ids)
    # print("field_map:", field_map)
    # try to use sql if field mapping is good to go
    # 如果字段映射存在，则使用SQL检索
    if field_map:
        chat_logger.info("Use SQL to retrieval:{}".format(questions[-1]))
        ans = use_sql(questions[-1], field_map, dialog.tenant_id, chat_mdl, prompt_config.get("quote", True))
        if ans:
            yield ans
            return
    # 检查提示词配置中的参数是否存在
    for p in prompt_config["parameters"]:
        if p["key"] == "knowledge":
            continue
        if p["key"] not in kwargs and not p["optional"]:
            raise KeyError("Miss parameter: " + p["key"])
        if p["key"] not in kwargs:
            prompt_config["system"] = prompt_config["system"].replace(
                "{%s}" % p["key"], " ")
    # 检查重排序模型是否存在
    rerank_mdl = None
    if dialog.rerank_id:
        rerank_mdl = LLMBundle(dialog.tenant_id, LLMType.RERANK, dialog.rerank_id)
    # 将问题复制一遍，用于检索
    for _ in range(len(questions) // 2):
        questions.append(questions[-1])
    # 如果提示词配置中没有knowledge参数，则初始化检索结果
    if "knowledge" not in [p["key"] for p in prompt_config["parameters"]]:
        kbinfos = {"total": 0, "chunks": [], "doc_aggs": []}
    else:
        # 检索
        chat_logger.info(f"Starting retrieval with params: tenant_id={dialog.tenant_id}, kb_ids={dialog.kb_ids}")
        # print(f"Starting retrieval with params: tenant_id={dialog.tenant_id}, kb_ids={dialog.kb_ids}")
        kbinfos = retrievaler.retrieval(" ".join(questions), embd_mdl, dialog.tenant_id, dialog.kb_ids, 1, dialog.top_n,
                                        dialog.similarity_threshold,
                                        dialog.vector_similarity_weight,
                                        doc_ids=kwargs["doc_ids"].split(",") if "doc_ids" in kwargs else None,
                                        top=1024, aggs=False, rerank_mdl=rerank_mdl)
        # print("Retrieval results:", kbinfos)
        chat_logger.info(f"Retrieval results: {kbinfos}")
    # 获取检索结果
    knowledges = [ck["content_with_weight"] for ck in kbinfos["chunks"]]
    # print("knowledges:", knowledges)
    # 如果提示词配置中启用了自RAG，则重写问题并重新检索
    if dialog.prompt_config.get("self_rag") and not relevant(dialog.tenant_id, dialog.llm_id, questions[-1], knowledges):
        questions[-1] = rewrite(dialog.tenant_id, dialog.llm_id, questions[-1])
        kbinfos = retrievaler.retrieval(" ".join(questions), embd_mdl, dialog.tenant_id, dialog.kb_ids, 1, dialog.top_n,
                                        dialog.similarity_threshold,
                                        dialog.vector_similarity_weight,
                                        doc_ids=kwargs["doc_ids"].split(",") if "doc_ids" in kwargs else None,
                                        top=1024, aggs=False, rerank_mdl=rerank_mdl)
        knowledges = [ck["content_with_weight"] for ck in kbinfos["chunks"]]
    # 打印检索结果
    chat_logger.info(
        "{}->{}".format(" ".join(questions), "\n->".join(knowledges)))
    # 如果检索结果为空，则返回提示词配置中的空响应
    if not knowledges and prompt_config.get("empty_response"):
        yield {"answer": prompt_config["empty_response"], "reference": kbinfos}
        return {"answer": prompt_config["empty_response"], "reference": kbinfos}
    # 将检索结果添加到提示词配置中
    kwargs["knowledge"] = "\n".join(knowledges)
    gen_conf = dialog.llm_setting
    # 构建提示词
    msg = [{"role": "system", "content": prompt_config["system"].format(**kwargs)}]
    msg.extend([{"role": m["role"], "content": m["content"]}
                for m in messages if m["role"] != "system"])
    # 检查提示词是否超出最大长度
    used_token_count, msg = message_fit_in(msg, int(max_tokens * 0.97))
    assert len(msg) >= 2, f"message_fit_in has bug: {msg}"
    # 检查最大token是否存在
    if "max_tokens" in gen_conf:
        gen_conf["max_tokens"] = min(
            gen_conf["max_tokens"],
            max_tokens - used_token_count)
    # 装饰答案
    def decorate_answer(answer):
        nonlocal prompt_config, knowledges, kwargs, kbinfos
        if knowledges and (prompt_config.get("quote", True) and kwargs.get("quote", True)):
            answer, idx = retrievaler.insert_citations(answer,
                                                       [ck["content_ltks"]
                                                        for ck in kbinfos["chunks"]],
                                                       [ck["vector"]
                                                        for ck in kbinfos["chunks"]],
                                                       embd_mdl,
                                                       tkweight=1 - dialog.vector_similarity_weight,
                                                       vtweight=dialog.vector_similarity_weight)
            idx = set([kbinfos["chunks"][int(i)]["doc_id"] for i in idx])
            recall_docs = [
                d for d in kbinfos["doc_aggs"] if d["doc_id"] in idx]
            if not recall_docs: recall_docs = kbinfos["doc_aggs"]
            kbinfos["doc_aggs"] = recall_docs
        # 复制检索结果
        refs = deepcopy(kbinfos)
        # 删除检索结果中的vector
        for c in refs["chunks"]:
            if c.get("vector"):
                del c["vector"]
        # 如果答案中包含无效密钥，则添加提示信息
        if answer.lower().find("invalid key") >= 0 or answer.lower().find("invalid api") >= 0:
            answer += " Please set LLM API-Key in 'User Setting -> Model Providers -> API-Key'"
        return {"answer": answer, "reference": refs}

    # 如果启用了流式输出，则逐个生成答案
    if stream:
        answer = ""
        for ans in chat_mdl.chat_streamly(msg[0]["content"], msg[1:], gen_conf):
            answer = ans
            yield {"answer": answer, "reference": {}}
        yield decorate_answer(answer)
    else:
        # 否则，一次性生成答案
        answer = chat_mdl.chat(
            msg[0]["content"], msg[1:], gen_conf)
        chat_logger.info("User: {}|Assistant: {}".format(
            msg[-1]["content"], answer))
        yield decorate_answer(answer)


def use_sql(question, field_map, tenant_id, chat_mdl, quota=True):
    sys_prompt = "你是一个DBA。你需要这对以下表的字段结构，根据用户的问题列表，写出最后一个问题对应的SQL。"
    user_promt = """
表名：{}；
数据库表字段说明如下：
{}

问题如下：
{}
请写出SQL, 且只要SQL，不要有其他说明及文字。
""".format(
        index_name(tenant_id),
        "\n".join([f"{k}: {v}" for k, v in field_map.items()]),
        question
    )
    tried_times = 0

    def get_table():
        nonlocal sys_prompt, user_promt, question, tried_times
        sql = chat_mdl.chat(sys_prompt, [{"role": "user", "content": user_promt}], {
            "temperature": 0.06})
        print(user_promt, sql)
        chat_logger.info(f"“{question}”==>{user_promt} get SQL: {sql}")
        sql = re.sub(r"[\r\n]+", " ", sql.lower())
        sql = re.sub(r".*select ", "select ", sql.lower())
        sql = re.sub(r" +", " ", sql)
        sql = re.sub(r"([;；]|```).*", "", sql)
        if sql[:len("select ")] != "select ":
            return None, None
        if not re.search(r"((sum|avg|max|min)\(|group by )", sql.lower()):
            if sql[:len("select *")] != "select *":
                sql = "select doc_id,docnm_kwd," + sql[6:]
            else:
                flds = []
                for k in field_map.keys():
                    if k in forbidden_select_fields4resume:
                        continue
                    if len(flds) > 11:
                        break
                    flds.append(k)
                sql = "select doc_id,docnm_kwd," + ",".join(flds) + sql[8:]

        print(f"“{question}” get SQL(refined): {sql}")

        chat_logger.info(f"“{question}” get SQL(refined): {sql}")
        tried_times += 1
        return retrievaler.sql_retrieval(sql, format="json"), sql

    tbl, sql = get_table()
    if tbl is None:
        return None
    if tbl.get("error") and tried_times <= 2:
        user_promt = """
        表名：{}；
        数据库表字段说明如下：
        {}

        问题如下：
        {}

        你上一次给出的错误SQL如下：
        {}

        后台报错如下：
        {}

        请纠正SQL中的错误再写一遍，且只要SQL，不要有其他说明及文字。
        """.format(
            index_name(tenant_id),
            "\n".join([f"{k}: {v}" for k, v in field_map.items()]),
            question, sql, tbl["error"]
        )
        tbl, sql = get_table()
        chat_logger.info("TRY it again: {}".format(sql))

    chat_logger.info("GET table: {}".format(tbl))
    print(tbl)
    if tbl.get("error") or len(tbl["rows"]) == 0:
        return None

    docid_idx = set([ii for ii, c in enumerate(
        tbl["columns"]) if c["name"] == "doc_id"])
    docnm_idx = set([ii for ii, c in enumerate(
        tbl["columns"]) if c["name"] == "docnm_kwd"])
    clmn_idx = [ii for ii in range(
        len(tbl["columns"])) if ii not in (docid_idx | docnm_idx)]

    # compose markdown table
    clmns = "|" + "|".join([re.sub(r"(/.*|（[^（）]+）)", "", field_map.get(tbl["columns"][i]["name"],
                                                                        tbl["columns"][i]["name"])) for i in
                            clmn_idx]) + ("|Source|" if docid_idx and docid_idx else "|")

    line = "|" + "|".join(["------" for _ in range(len(clmn_idx))]) + \
           ("|------|" if docid_idx and docid_idx else "")

    rows = ["|" +
            "|".join([rmSpace(str(r[i])) for i in clmn_idx]).replace("None", " ") +
            "|" for r in tbl["rows"]]
    if quota:
        rows = "\n".join([r + f" ##{ii}$$ |" for ii, r in enumerate(rows)])
    else:
        rows = "\n".join([r + f" ##{ii}$$ |" for ii, r in enumerate(rows)])
    rows = re.sub(r"T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+Z)?\|", "|", rows)

    if not docid_idx or not docnm_idx:
        chat_logger.warning("SQL missing field: " + sql)
        return {
            "answer": "\n".join([clmns, line, rows]),
            "reference": {"chunks": [], "doc_aggs": []}
        }

    docid_idx = list(docid_idx)[0]
    docnm_idx = list(docnm_idx)[0]
    doc_aggs = {}
    for r in tbl["rows"]:
        if r[docid_idx] not in doc_aggs:
            doc_aggs[r[docid_idx]] = {"doc_name": r[docnm_idx], "count": 0}
        doc_aggs[r[docid_idx]]["count"] += 1
    return {
        "answer": "\n".join([clmns, line, rows]),
        "reference": {"chunks": [{"doc_id": r[docid_idx], "docnm_kwd": r[docnm_idx]} for r in tbl["rows"]],
                      "doc_aggs": [{"doc_id": did, "doc_name": d["doc_name"], "count": d["count"]} for did, d in
                                   doc_aggs.items()]}
    }


def relevant(tenant_id, llm_id, question, contents: list):
    chat_mdl = LLMBundle(tenant_id, LLMType.CHAT, llm_id)
    prompt = """
        You are a grader assessing relevance of a retrieved document to a user question. 
        It does not need to be a stringent test. The goal is to filter out erroneous retrievals.
        If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. 
        Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question.
        No other words needed except 'yes' or 'no'.
    """
    if not contents:return False
    contents = "Documents: \n" + "   - ".join(contents)
    contents = f"Question: {question}\n" + contents
    if num_tokens_from_string(contents) >= chat_mdl.max_length - 4:
        contents = encoder.decode(encoder.encode(contents)[:chat_mdl.max_length - 4])
    ans = chat_mdl.chat(prompt, [{"role": "user", "content": contents}], {"temperature": 0.01})
    if ans.lower().find("yes") >= 0: return True
    return False


def rewrite(tenant_id, llm_id, question):
    chat_mdl = LLMBundle(tenant_id, LLMType.CHAT, llm_id)
    prompt = """
        You are an expert at query expansion to generate a paraphrasing of a question.
        I can't retrieval relevant information from the knowledge base by using user's question directly.     
        You need to expand or paraphrase user's question by multiple ways such as using synonyms words/phrase, 
        writing the abbreviation in its entirety, adding some extra descriptions or explanations, 
        changing the way of expression, translating the original question into another language (English/Chinese), etc. 
        And return 5 versions of question and one is from translation.
        Just list the question. No other words are needed.
    """
    ans = chat_mdl.chat(prompt, [{"role": "user", "content": question}], {"temperature": 0.8})
    return ans
