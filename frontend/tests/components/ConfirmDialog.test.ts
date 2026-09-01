import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue';

describe('ConfirmDialog', () => {
  const mountDialog = (overrides = {}) => mount(ConfirmDialog, {
    props: { modelValue: true, title: '确认停用工具', description: '停用后将无法继续执行。', ...overrides },
    global: { stubs: {
      'el-dialog': { props: ['modelValue', 'title'], template: '<div v-if="modelValue"><h2>{{ title }}</h2><slot /><slot name="footer" /></div>' },
      'el-button': { props: ['loading', 'disabled', 'type'], emits: ['click'], template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
    } },
  });

  it('renders business confirmation text and action labels', () => {
    const wrapper = mountDialog({ confirmText: '确认停用', cancelText: '返回', danger: true });
    expect(wrapper.text()).toContain('确认停用工具');
    expect(wrapper.text()).toContain('停用后将无法继续执行。');
    expect(wrapper.text()).toContain('确认停用');
    expect(wrapper.text()).toContain('返回');
  });

  it('emits confirm and cancel without embedding domain logic', async () => {
    const wrapper = mountDialog();
    const buttons = wrapper.findAll('button');
    await buttons[0].trigger('click');
    await buttons[1].trigger('click');
    expect(wrapper.emitted('cancel')).toHaveLength(1);
    expect(wrapper.emitted('confirm')).toHaveLength(1);
  });

  it('blocks closing actions while confirmation is loading', () => {
    const wrapper = mountDialog({ loading: true });
    const buttons = wrapper.findAll('button');
    expect(buttons[0].attributes('disabled')).toBeDefined();
  });
});
