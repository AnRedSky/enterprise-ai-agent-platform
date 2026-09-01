import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ElTable, ElTableColumn } from 'element-plus';
import ToolWorkbench from '@/views/tools/components/ToolWorkbench.vue';
import PageHeader from '@/components/ui/PageHeader.vue';
import PageToolbar from '@/components/ui/PageToolbar.vue';
import SurfaceCard from '@/components/ui/SurfaceCard.vue';
import StatePanel from '@/components/ui/StatePanel.vue';
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue';

const api = vi.hoisted(() => ({ listTools: vi.fn(), listAgents: vi.fn(), createTool: vi.fn(), disableTool: vi.fn(), enableTool: vi.fn(), unbindTool: vi.fn() }));
vi.mock('@/api/auth', () => ({ getRoles: () => ['admin'] }));
vi.mock('@/api/agents', () => ({ listAgents: api.listAgents }));
vi.mock('@/api/tools', () => ({ bindTool: vi.fn(), createTool: api.createTool, disableTool: api.disableTool, enableTool: api.enableTool, executeTool: vi.fn(), listTools: api.listTools, unbindTool: api.unbindTool }));
vi.mock('@/utils/toolError', () => ({ getToolUserError: (_error: unknown, fallback: string) => fallback }));

function mountPage() {
  return mount(ToolWorkbench, { global: { components: { ElTable, ElTableColumn }, directives: { loading: () => undefined }, stubs: {
    'el-button': { emits: ['click'], template: '<button @click="$emit(\'click\')"><slot /></button>' }, 'el-alert': true, 'el-icon': { template: '<span><slot /></span>' }, 'el-table': false, 'el-table-column': false, 'el-empty': true, 'el-dialog': true,
    'el-form': true, 'el-form-item': true, 'el-input': true, 'el-select': true, 'el-option': true, 'el-tag': true,
  } } });
}

describe('ToolWorkbench UI-03/UI-05 migration', () => {
  beforeEach(() => { vi.resetAllMocks(); api.listTools.mockResolvedValue([]); api.listAgents.mockResolvedValue([]); api.createTool.mockResolvedValue({ id: 't1' }); });
  it('uses shared PageHeader, PageToolbar and SurfaceCard patterns', async () => {
    api.listTools.mockResolvedValue([{ id: 't1', name: 'Tool', description: 'test', enabled: true }]);
    const wrapper = mountPage(); await flushPromises();
    expect(wrapper.findComponent(PageHeader).exists()).toBe(true);
    expect(wrapper.findComponent(PageToolbar).exists()).toBe(true);
    expect(wrapper.findComponent(SurfaceCard).exists()).toBe(true);
    expect(wrapper.findComponent(PageHeader).props('title')).toBe('工具管理');
    expect(wrapper.findComponent(PageToolbar).props('title')).toBe('工具列表');
  });
  it('renders the shared empty-state contract when no tools are returned', async () => {
    const wrapper = mountPage(); await flushPromises();
    const state = wrapper.findComponent(StatePanel);
    expect(state.exists()).toBe(true);
    expect(state.props('state')).toBe('empty');
    expect(state.props('title')).toBe('暂无可用工具');
    expect(state.props('description')).toBe('当前没有可用工具，请创建工具或启用已有工具。');
  });
  it('keeps the administrator creation action in the PageHeader action slot', async () => {
    const wrapper = mountPage(); await flushPromises();
    expect(wrapper.findComponent(PageHeader).text()).toContain('创建工具');
  });
  it('routes destructive tool actions through the shared ConfirmDialog', async () => {
    api.listTools.mockResolvedValue([{ id: 't1', name: 'Tool', description: 'test', enabled: true }]);
    const wrapper = mountPage(); await flushPromises();
    const disableButton = wrapper.findAll('button').find((button) => button.text() === '停用');
    expect(disableButton).toBeDefined();
    await disableButton!.trigger('click');
    const confirm = wrapper.findComponent(ConfirmDialog);
    expect(confirm.exists()).toBe(true);
    expect(confirm.props('modelValue')).toBe(true);
    expect(confirm.props('title')).toBe('确认停用工具');
    expect(confirm.props('danger')).toBe(true);
    expect(confirm.props('description')).toContain('Tool');
  });
  it('rejects an empty tool name before calling the create API', async () => {
    const wrapper = mountPage(); await flushPromises();
    (wrapper.vm as any).createVisible = true;
    await (wrapper.vm as any).create();
    expect(api.createTool).not.toHaveBeenCalled();
    expect((wrapper.vm as any).createErrors.name).toBe('请输入工具名称。');
  });
  it('rejects non-object input schema before calling the create API', async () => {
    const wrapper = mountPage(); await flushPromises();
    (wrapper.vm as any).createVisible = true;
    (wrapper.vm as any).createForm = { name: 'Tool', description: '', endpoint: '', input_schema: '[]' };
    await (wrapper.vm as any).create();
    expect(api.createTool).not.toHaveBeenCalled();
    expect((wrapper.vm as any).createErrors.input_schema).toBe('输入结构必须是 JSON 对象。');
  });
  it('submits normalized create data and closes only after success', async () => {
    const wrapper = mountPage(); await flushPromises();
    (wrapper.vm as any).createVisible = true;
    (wrapper.vm as any).createForm = { name: '  Tool  ', description: '  desc  ', endpoint: '  https://example.test/tool  ', input_schema: '{"type":"object"}' };
    await (wrapper.vm as any).create();
    expect(api.createTool).toHaveBeenCalledWith({ name: 'Tool', description: 'desc', endpoint: 'https://example.test/tool', input_schema: { type: 'object' }, enabled: true });
    expect((wrapper.vm as any).createVisible).toBe(false);
    expect((wrapper.vm as any).createForm).toEqual({ name: '', description: '', endpoint: '', input_schema: '{}' });
  });
  it('keeps form input when the create API fails', async () => {
    api.createTool.mockRejectedValueOnce(new Error('backend failure'));
    const wrapper = mountPage(); await flushPromises();
    (wrapper.vm as any).createVisible = true;
    const form = { name: 'Tool', description: 'desc', endpoint: '', input_schema: '{"type":"object"}' };
    (wrapper.vm as any).createForm = { ...form };
    await (wrapper.vm as any).create();
    expect((wrapper.vm as any).createVisible).toBe(true);
    expect((wrapper.vm as any).createForm).toEqual(form);
  });
});
