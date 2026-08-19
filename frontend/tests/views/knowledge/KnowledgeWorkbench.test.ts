import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import KnowledgeWorkbench from "@/views/knowledge/components/KnowledgeWorkbench.vue";
import * as api from "@/api/knowledge";

vi.mock("@/api/knowledge",()=>({listKnowledgeBases:vi.fn(),listDocuments:vi.fn(),listVersions:vi.fn(),listChunks:vi.fn(),createKnowledgeBase:vi.fn(),createDocument:vi.fn(),createVersion:vi.fn(),deleteDocument:vi.fn(),ingestVersion:vi.fn(),retrieveKnowledge:vi.fn(),updateDocument:vi.fn(),updateKnowledgeBase:vi.fn()}));

describe("KnowledgeWorkbench",()=>{
  it("renders knowledge and retrieval sections",async()=>{vi.mocked(api.listKnowledgeBases).mockResolvedValue({items:[],total:0,page:1,page_size:20});const wrapper=mount(KnowledgeWorkbench,{global:{stubs:{"el-table":{template:"<div><slot/></div>"},"el-table-column":{template:"<div><slot :row="{}"/></div>"},"el-card":{template:"<section><slot name=header/><slot/></section>"},"el-button":true,"el-input":true,"el-input-number":true,"el-alert":true,"el-empty":true,"el-dialog":true,"el-form":true,"el-form-item":true}}});await vi.waitFor(()=>expect(api.listKnowledgeBases).toHaveBeenCalled());expect(wrapper.text()).toContain("Knowledge 知识管理");expect(wrapper.text()).toContain("Retrieval Debug")});
  it("shows API failure state",async()=>{vi.mocked(api.listKnowledgeBases).mockRejectedValue(new Error("network"));const wrapper=mount(KnowledgeWorkbench,{global:{stubs:{"el-table":true,"el-table-column":true,"el-card":{template:"<section><slot name=header/><slot/></section>"},"el-button":true,"el-input":true,"el-input-number":true,"el-alert":{template:"<div>{{title}}</div>",props:["title"]},"el-empty":true,"el-dialog":true,"el-form":true,"el-form-item":true}}});await vi.waitFor(()=>expect(wrapper.text()).toContain("network"))});
});
