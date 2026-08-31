import { describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import AuditLogPanel from "@/views/audit-log/components/AuditLogPanel.vue";
import StatePanel from "@/components/ui/StatePanel.vue";
const api = vi.hoisted(() => ({ auditLogs: vi.fn() }));
vi.mock("@/api/runtime",()=>({runtimeApi:{auditLogs: api.auditLogs}}));
vi.mock("vue-router",()=>({useRouter:()=>({push:vi.fn()})}));
function mountView(){return mount(AuditLogPanel,{global:{stubs:{"el-button":true,"el-select":true,"el-option":true,"el-table":true,"el-table-column":true,"el-pagination":true}}})}
describe("AuditLog UI-04 states",()=>{
 it("renders loading then success",async()=>{let resolve!:(v:any)=>void;api.auditLogs.mockReturnValueOnce(new Promise(r=>{resolve=r}));const wrapper=mountView();expect(wrapper.findComponent(StatePanel).props("state")).toBe("loading");resolve({data:{items:[{id:"a1",action:"execute",status:"success"}],total:1}});await flushPromises();expect(wrapper.find(".table-wrap").exists()).toBe(true);expect(wrapper.text()).toContain("审计日志已更新")});
 it.each([["empty",{data:{items:[],total:0}},"暂无符合条件的审计日志"],["error",Promise.reject(new Error("network")),"审计日志加载失败"],["permission",Promise.reject({response:{status:403}}),"无权查看审计日志"]] as const)("renders %s",async(state,response,title)=>{api.auditLogs.mockReturnValueOnce(response);const wrapper=mountView();await flushPromises();expect(wrapper.findComponent(StatePanel).props("state")).toBe(state);expect(wrapper.text()).toContain(title)});
});
