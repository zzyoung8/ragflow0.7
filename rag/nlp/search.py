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

import json
import re
from copy import deepcopy

from elasticsearch_dsl import Q, Search
from typing import List, Optional, Dict, Union
from dataclasses import dataclass

from rag.settings import es_logger
from rag.utils import rmSpace
from rag.nlp import rag_tokenizer, query
import numpy as np


def index_name(uid): return f"ragflow_{uid}"


class Dealer:
    def __init__(self, es):
        self.qryr = query.EsQueryer(es)
        self.qryr.flds = [
            "title_tks^10",
            "title_sm_tks^5",
            "important_kwd^30",
            "important_tks^20",
            "content_ltks^2",
            "content_sm_ltks"]
        self.es = es

    @dataclass
    class SearchResult:
        total: int
        ids: List[str]
        query_vector: List[float] = None
        field: Optional[Dict] = None
        highlight: Optional[Dict] = None
        aggregation: Union[List, Dict, None] = None
        keywords: Optional[List[str]] = None
        group_docs: List[List] = None

    def _vector(self, txt, emb_mdl, sim=0.8, topk=10):
        qv, c = emb_mdl.encode_queries(txt)
        return {
            "field": "q_%d_vec" % len(qv),
            "k": topk,
            "similarity": sim,
            "num_candidates": topk * 2,
            "query_vector": [float(v) for v in qv]
        }

    def search(self, req, idxnm, emb_mdl=None):
        """
        执行搜索操作，支持关键词搜索和向量搜索
        
        Args:
            req: 搜索请求参数字典
            idxnm: 索引名称
            emb_mdl: 嵌入模型，用于向量搜索，默认为None
        
        Returns:
            SearchResult: 包含搜索结果的数据类
        """
        # 从请求中获取搜索问题
        qst = req.get("question", "")
        
        # 使用查询器构建基础查询条件和提取关键词
        bqry, keywords = self.qryr.question(qst)
        # print("bqry_before:", bqry)
        def add_filters(bqry):
            """内部函数：添加过滤条件到查询对象"""
            nonlocal req
            # 添加知识库ID过滤
            if req.get("kb_ids"):
                bqry.filter.append(Q("terms", kb_id=req["kb_ids"]))
            # 添加文档ID过滤
            if req.get("doc_ids"):
                bqry.filter.append(Q("terms", doc_id=req["doc_ids"]))
            # 添加可用性过滤
            if "available_int" in req:
                if req["available_int"] == 0:
                    # available_int=0 表示查询未启用的文档
                    bqry.filter.append(Q("range", available_int={"lt": 1}))
                else:
                    # available_int!=0 表示查询已启用的文档
                    bqry.filter.append(
                        Q("bool", must_not=Q("range", available_int={"lt": 1})))
            return bqry

        # 应用过滤条件并设置boost值
        bqry = add_filters(bqry)
        # print("bqry_after:", bqry)
        bqry.boost = 0.05
        
        # 初始化Search对象并设置分页参数
        s = Search()
        pg = int(req.get("page", 1)) - 1  # 页码（从0开始）
        topk = int(req.get("topk", 1024))  # 最大返回数量
        ps = int(req.get("size", topk))    # 每页大小
        
        # 定义需要返回的字段列表
        src = req.get("fields", ["docnm_kwd", "content_ltks", "kb_id", "img_id", "title_tks", "important_kwd",
                                "image_id", "doc_id", "q_512_vec", "q_768_vec", "position_int",
                                "q_1024_vec", "q_1536_vec", "available_int", "content_with_weight"])
        
        # 设置分页和高亮
        s = s.query(bqry)[pg * ps:(pg + 1) * ps]
        s = s.highlight("content_ltks")
        s = s.highlight("title_ltks")
        
        # 如果没有搜索问题，设置排序规则
        if not qst:
            if not req.get("sort"):
                # 默认按创建时间倒序
                s = s.sort({"create_timestamp_flt": {"order": "desc", "unmapped_type": "float"}})
            else:
                # 自定义排序：按页码、置顶状态和创建时间排序
                s = s.sort(
                    {"page_num_int": {"order": "asc", "unmapped_type": "float",
                                    "mode": "avg", "numeric_type": "double"}},
                    {"top_int": {"order": "asc", "unmapped_type": "float",
                                "mode": "avg", "numeric_type": "double"}},
                    {"create_timestamp_flt": {"order": "desc", "unmapped_type": "float"}}
                )

        # 如果有搜索问题，设置高亮选项
        if qst:
            s = s.highlight_options(
                fragment_size=120,          # 高亮片段大小
                number_of_fragments=5,      # 返回的高亮片段数量
                boundary_scanner_locale="zh-CN",  # 设置中文分句
                boundary_scanner="SENTENCE",      # 按句子分割
                boundary_chars=",./;:\\!()，。？：！……（）——、"  # 分句标点符号
            )
        
        # 转换为字典格式
        s = s.to_dict()
        q_vec = []
        
        # 处理向量搜索
        if req.get("vector"):
            assert emb_mdl, "No embedding model selected"
            # 添加KNN搜索配置
            s["knn"] = self._vector(qst, emb_mdl, req.get("similarity", 0.1), topk)
            s["knn"]["filter"] = bqry.to_dict()
            if "highlight" in s:
                del s["highlight"]
            q_vec = s["knn"]["query_vector"]
        
        # 执行搜索
        es_logger.info("【Q】: {}".format(json.dumps(s)))
        # print("idxnm:", idxnm)
        res = self.es.search(deepcopy(s), idxnm=idxnm, timeout="600s", src=src)
        es_logger.info("TOTAL: {}".format(self.es.getTotal(res)))
        # print("rearch_res:", res)
        # 如果向量搜索没有结果，降低匹配要求重试
        if self.es.getTotal(res) == 0 and "knn" in s:
            bqry, _ = self.qryr.question(qst, min_match="10%")
            bqry = add_filters(bqry)
            s["query"] = bqry.to_dict()
            s["knn"]["filter"] = bqry.to_dict()
            s["knn"]["similarity"] = 0.17
            res = self.es.search(s, idxnm=idxnm, timeout="600s", src=src)
            es_logger.info("【Q】: {}".format(json.dumps(s)))

        # 处理关键词
        kwds = set([])
        for k in keywords:
            kwds.add(k)
            # 对关键词进行细粒度分词
            for kk in rag_tokenizer.fine_grained_tokenize(k).split(" "):
                if len(kk) < 2 or kk in kwds:
                    continue
                kwds.add(kk)

        # 获取文档名称聚合结果
        aggs = self.getAggregation(res, "docnm_kwd")

        # 返回搜索结果
        return self.SearchResult(
            total=self.es.getTotal(res),        # 总结果数
            ids=self.es.getDocIds(res),         # 文档ID列表
            query_vector=q_vec,                 # 查询向量
            aggregation=aggs,                   # 聚合结果
            highlight=self.getHighlight(res),   # 高亮结果
            field=self.getFields(res, src),     # 字段值
            keywords=list(kwds)                 # 关键词列表
        )

    def getAggregation(self, res, g):
        if not "aggregations" in res or "aggs_" + g not in res["aggregations"]:
            return
        bkts = res["aggregations"]["aggs_" + g]["buckets"]
        return [(b["key"], b["doc_count"]) for b in bkts]

    def getHighlight(self, res):
        def rmspace(line):
            eng = set(list("qwertyuioplkjhgfdsazxcvbnm"))
            r = []
            for t in line.split(" "):
                if not t:
                    continue
                if len(r) > 0 and len(
                        t) > 0 and r[-1][-1] in eng and t[0] in eng:
                    r.append(" ")
                r.append(t)
            r = "".join(r)
            return r

        ans = {}
        for d in res["hits"]["hits"]:
            hlts = d.get("highlight")
            if not hlts:
                continue
            ans[d["_id"]] = "".join([a for a in list(hlts.items())[0][1]])
        return ans

    def getFields(self, sres, flds):
        res = {}
        if not flds:
            return {}
        for d in self.es.getSource(sres):
            m = {n: d.get(n) for n in flds if d.get(n) is not None}
            for n, v in m.items():
                if isinstance(v, type([])):
                    m[n] = "\t".join([str(vv) if not isinstance(
                        vv, list) else "\t".join([str(vvv) for vvv in vv]) for vv in v])
                    continue
                if not isinstance(v, type("")):
                    m[n] = str(m[n])
                if n.find("tks") > 0:
                    m[n] = rmSpace(m[n])

            if m:
                res[d["id"]] = m
        return res

    @staticmethod
    def trans2floats(txt):
        return [float(t) for t in txt.split("\t")]

    def insert_citations(self, answer, chunks, chunk_v,
                         embd_mdl, tkweight=0.1, vtweight=0.9):
        """
        为回答插入引用标记
        
        Args:
            answer: 需要添加引用的回答文本
            chunks: 知识库中的文本片段列表
            chunk_v: 知识库文本片段的向量表示
            embd_mdl: 嵌入模型,用于计算文本向量
            tkweight: token相似度权重,默认0.1
            vtweight: 向量相似度权重,默认0.9
            
        Returns:
            tuple: (添加引用后的文本, 引用的chunk索引集合)
        """
        # 确保chunks和chunk_v长度一致
        assert len(chunks) == len(chunk_v)
        
        # 按代码块和句子分割文本
        pieces = re.split(r"(```)", answer)
        if len(pieces) >= 3:  # 包含代码块
            i = 0
            pieces_ = []
            while i < len(pieces):
                if pieces[i] == "```":  # 处理代码块
                    st = i
                    i += 1
                    while i < len(pieces) and pieces[i] != "```":
                        i += 1
                    if i < len(pieces):
                        i += 1
                    pieces_.append("".join(pieces[st: i]) + "\n")
                else:  # 处理普通文本
                    pieces_.extend(
                        re.split(
                            r"([^\|][；。？!！\n]|[a-z][.?;!][ \n])",
                            pieces[i]))
                    i += 1
            pieces = pieces_
        else:  # 不包含代码块,直接按句子分割
            pieces = re.split(r"([^\|][；。？!！\n]|[a-z][.?;!][ \n])", answer)
            
        # 修正分割结果,确保标点符号跟随正确的句子
        for i in range(1, len(pieces)):
            if re.match(r"([^\|][；。？!！\n]|[a-z][.?;!][ \n])", pieces[i]):
                pieces[i - 1] += pieces[i][0]
                pieces[i] = pieces[i][1:]
                
        # 过滤太短的片段
        idx = []
        pieces_ = []
        for i, t in enumerate(pieces):
            if len(t) < 5:
                continue
            idx.append(i)
            pieces_.append(t)
        es_logger.info("{} => {}".format(answer, pieces_))
        if not pieces_:
            return answer, set([])

        # 计算文本片段的向量表示
        ans_v, _ = embd_mdl.encode(pieces_)
        assert len(ans_v[0]) == len(chunk_v[0]), "The dimension of query and chunk do not match: {} vs. {}".format(
            len(ans_v[0]), len(chunk_v[0]))

        # 对知识库文本进行分词
        chunks_tks = [rag_tokenizer.tokenize(self.qryr.rmWWW(ck)).split(" ")
                      for ck in chunks]
                      
        # 计算相似度并添加引用
        cites = {}
        thr = 0.63  # 相似度阈值
        while thr>0.3 and len(cites.keys()) == 0 and pieces_ and chunks_tks:
            for i, a in enumerate(pieces_):
                # 计算混合相似度
                sim, tksim, vtsim = self.qryr.hybrid_similarity(ans_v[i],
                                                                chunk_v,
                                                                rag_tokenizer.tokenize(
                                                                    self.qryr.rmWWW(pieces_[i])).split(" "),
                                                                chunks_tks,
                                                                tkweight, vtweight)
                mx = np.max(sim) * 0.99
                es_logger.info("{} SIM: {}".format(pieces_[i], mx))
                if mx < thr:
                    continue
                # 选择相似度最高的4个chunk作为引用
                cites[idx[i]] = list(
                    set([str(ii) for ii in range(len(chunk_v)) if sim[ii] > mx]))[:4]
            thr *= 0.8  # 降低阈值继续尝试

        # 组装最终结果
        res = ""
        seted = set([])  # 记录已添加的引用
        for i, p in enumerate(pieces):
            res += p
            if i not in idx:
                continue
            if i not in cites:
                continue
            for c in cites[i]:
                assert int(c) < len(chunk_v)
            for c in cites[i]:
                if c in seted:
                    continue
                res += f" ##{c}$$"  # 添加引用标记
                seted.add(c)

        return res, seted

    def rerank(self, sres, query, tkweight=0.3,
               vtweight=0.7, cfield="content_ltks"):
        _, keywords = self.qryr.question(query)
        ins_embd = [
            Dealer.trans2floats(
                sres.field[i].get("q_%d_vec" % len(sres.query_vector), "\t".join(["0"] * len(sres.query_vector)))) for i in sres.ids]
        if not ins_embd:
            return [], [], []

        for i in sres.ids:
            if isinstance(sres.field[i].get("important_kwd", []), str):
                sres.field[i]["important_kwd"] = [sres.field[i]["important_kwd"]]
        ins_tw = []
        for i in sres.ids:
            content_ltks = sres.field[i][cfield].split(" ")
            title_tks = [t for t in sres.field[i].get("title_tks", "").split(" ") if t]
            important_kwd = sres.field[i].get("important_kwd", [])
            tks = content_ltks + title_tks + important_kwd
            ins_tw.append(tks)

        sim, tksim, vtsim = self.qryr.hybrid_similarity(sres.query_vector,
                                                        ins_embd,
                                                        keywords,
                                                        ins_tw, tkweight, vtweight)
        return sim, tksim, vtsim

    def rerank_by_model(self, rerank_mdl, sres, query, tkweight=0.3,
               vtweight=0.7, cfield="content_ltks"):
        _, keywords = self.qryr.question(query)

        for i in sres.ids:
            if isinstance(sres.field[i].get("important_kwd", []), str):
                sres.field[i]["important_kwd"] = [sres.field[i]["important_kwd"]]
        ins_tw = []
        for i in sres.ids:
            content_ltks = sres.field[i][cfield].split(" ")
            title_tks = [t for t in sres.field[i].get("title_tks", "").split(" ") if t]
            important_kwd = sres.field[i].get("important_kwd", [])
            tks = content_ltks + title_tks + important_kwd
            ins_tw.append(tks)

        tksim = self.qryr.token_similarity(keywords, ins_tw)
        vtsim,_ = rerank_mdl.similarity(" ".join(keywords), [rmSpace(" ".join(tks)) for tks in ins_tw])

        return tkweight*np.array(tksim) + vtweight*vtsim, tksim, vtsim

    def hybrid_similarity(self, ans_embd, ins_embd, ans, inst):
        return self.qryr.hybrid_similarity(ans_embd,
                                           ins_embd,
                                           rag_tokenizer.tokenize(ans).split(" "),
                                           rag_tokenizer.tokenize(inst).split(" "))

    def retrieval(self, question, embd_mdl, tenant_id, kb_ids, page, page_size, similarity_threshold=0.2,
                  vector_similarity_weight=0.3, top=1024, doc_ids=None, aggs=True, rerank_mdl=None):
        from api.db.services.knowledgebase_service import KnowledgebaseService
        from api.db.services.user_service import UserService
        ranks = {"total": 0, "chunks": [], "doc_aggs": {}}
        # 如果问题为空，则返回空结果
        if not question:
            return ranks
        # 构建检索请求
        req = {"kb_ids": kb_ids, "doc_ids": doc_ids, "size": page_size,
               "question": question, "vector": True, "topk": top,
               "similarity": similarity_threshold,
               "available_int": 1}
        # print("Search request:", req)
        # 执行检索
        kb_id = req["kb_ids"][0]
        shared = KnowledgebaseService.is_shared(kb_id)
        if shared == 1:
            admin_id = UserService.get_admin_id()
            # admin_id = "6e4490ee7c7911efa44bb42e99cad8a4"
            tenant_id = admin_id
        sres = self.search(req, index_name(tenant_id), embd_mdl)
        es_logger.info(f"Search results count: {len(sres.ids) if sres.ids else 0}")
        # 如果重排序模型存在，则使用重排序模型
        if rerank_mdl:
            sim, tsim, vsim = self.rerank_by_model(rerank_mdl,
                sres, question, 1 - vector_similarity_weight, vector_similarity_weight)
        else:
            # 否则，使用默认的混合相似度
            sim, tsim, vsim = self.rerank(
                sres, question, 1 - vector_similarity_weight, vector_similarity_weight)
        # 获取排序后的索引
        idx = np.argsort(sim * -1)
        # 获取嵌入维度
        dim = len(sres.query_vector)
        # 获取起始索引
        start_idx = (page - 1) * page_size
        # 遍历排序后的索引
        for i in idx:
            # 如果相似度小于阈值，则跳出循环
            if sim[i] < similarity_threshold:
                break
            # 增加总文档数
            ranks["total"] += 1
            # 减少起始索引
            start_idx -= 1
            # 如果起始索引大于等于0，则跳过
            if start_idx >= 0:
                continue
            # 如果文档数大于等于页面大小，则跳过
            if len(ranks["chunks"]) >= page_size:
                if aggs:
                    continue
                break
            # 获取文档ID
            id = sres.ids[i]
            # 获取文档名称
            dnm = sres.field[id]["docnm_kwd"]
            # 获取文档ID
            did = sres.field[id]["doc_id"]
            # 构建文档
            d = {
                "chunk_id": id,
                "content_ltks": sres.field[id]["content_ltks"],
                "content_with_weight": sres.field[id]["content_with_weight"],
                "doc_id": sres.field[id]["doc_id"],
                "docnm_kwd": dnm,
                "kb_id": sres.field[id]["kb_id"],
                "important_kwd": sres.field[id].get("important_kwd", []),
                "img_id": sres.field[id].get("img_id", ""),
                "similarity": sim[i],
                "vector_similarity": vsim[i],
                "term_similarity": tsim[i],
                "vector": self.trans2floats(sres.field[id].get("q_%d_vec" % dim, "\t".join(["0"] * dim))),
                "positions": sres.field[id].get("position_int", "").split("\t")
            }
            # 如果位置数是5的倍数，则转换为浮点数
            if len(d["positions"]) % 5 == 0:
                poss = []
                # 遍历位置数
                for i in range(0, len(d["positions"]), 5):
                    # 将位置数转换为浮点数
                    poss.append([float(d["positions"][i]), float(d["positions"][i + 1]), float(d["positions"][i + 2]),
                                 float(d["positions"][i + 3]), float(d["positions"][i + 4])])
                d["positions"] = poss
            # 将文档添加到结果中
            ranks["chunks"].append(d)
            # 如果文档名称不在文档聚合中，则初始化文档聚合
            if dnm not in ranks["doc_aggs"]:
                ranks["doc_aggs"][dnm] = {"doc_id": did, "count": 0}
            # 增加文档计数
            ranks["doc_aggs"][dnm]["count"] += 1
        # 将文档聚合转换为列表
        ranks["doc_aggs"] = [{"doc_name": k,
                              "doc_id": v["doc_id"],
                              "count": v["count"]} for k,
                             v in sorted(ranks["doc_aggs"].items(),
                                         key=lambda x:x[1]["count"] * -1)]
        # 返回结果
        return ranks

    def sql_retrieval(self, sql, fetch_size=128, format="json"):
        from api.settings import chat_logger
        sql = re.sub(r"[ `]+", " ", sql)
        sql = sql.replace("%", "")
        es_logger.info(f"Get es sql: {sql}")
        replaces = []
        for r in re.finditer(r" ([a-z_]+_l?tks)( like | ?= ?)'([^']+)'", sql):
            fld, v = r.group(1), r.group(3)
            match = " MATCH({}, '{}', 'operator=OR;minimum_should_match=30%') ".format(
                fld, rag_tokenizer.fine_grained_tokenize(rag_tokenizer.tokenize(v)))
            replaces.append(
                ("{}{}'{}'".format(
                    r.group(1),
                    r.group(2),
                    r.group(3)),
                    match))

        for p, r in replaces:
            sql = sql.replace(p, r, 1)
        chat_logger.info(f"To es: {sql}")

        try:
            tbl = self.es.sql(sql, fetch_size, format)
            return tbl
        except Exception as e:
            chat_logger.error(f"SQL failure: {sql} =>" + str(e))
            return {"error": str(e)}

    def chunk_list(self, doc_id, tenant_id, max_count=1024, fields=["docnm_kwd", "content_with_weight", "img_id"]):
        s = Search()
        s = s.query(Q("match", doc_id=doc_id))[0:max_count]
        s = s.to_dict()
        es_res = self.es.search(s, idxnm=index_name(tenant_id), timeout="600s", src=fields)
        res = []
        for index, chunk in enumerate(es_res['hits']['hits']):
            res.append({fld: chunk['_source'].get(fld) for fld in fields})
        return res
