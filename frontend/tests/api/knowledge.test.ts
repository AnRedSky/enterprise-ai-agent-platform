import { describe, expect, it, vi } from "vitest";
import { createKnowledgeBase, listDocuments, listKnowledgeBases, retrieveKnowledge } from "@/api/knowledge";
import { request } from "@/api/request";

describe("knowledge api",()=>{
  it("lists paginated knowledge bases",async()=>{vi.spyOn(request,"get").mockResolvedValueOnce({data:{items:[],total:0,page:1,page_size:20}} as never);await expect(listKnowledgeBases()).resolves.toEqual({items:[],total:0,page:1,page_size:20});expect(request.get).toHaveBeenCalledWith("/knowledge",{params:{page:1,page_size:20}})});
  it("lists documents for a knowledge base",async()=>{vi.spyOn(request,"get").mockResolvedValueOnce({data:{items:[],total:0,page:2,page_size:10}} as never);await listDocuments("kb-1",2,10);expect(request.get).toHaveBeenCalledWith("/knowledge/kb-1/documents",{params:{page:2,page_size:10}})});
  it("sends retrieval contract with scope",async()=>{vi.spyOn(request,"post").mockResolvedValueOnce({data:{query:"ai",top_k:3,results:[]}} as never);await retrieveKnowledge({query:"ai",top_k:3,knowledge_base_id:"kb-1"});expect(request.post).toHaveBeenCalledWith("/knowledge/retrieve",{query:"ai",top_k:3,knowledge_base_id:"kb-1"})});
  it("creates a knowledge base",async()=>{vi.spyOn(request,"post").mockResolvedValueOnce({data:{id:"kb-1"}} as never);await createKnowledgeBase({name:"kb",description:"",status:"active"});expect(request.post).toHaveBeenCalledWith("/knowledge",{name:"kb",description:"",status:"active"})});
});
