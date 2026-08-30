import { h, inject, provide, type InjectionKey, type Component } from "vue";

/**
 * 前端表格测试桩：保留表头、普通字段以及作用域插槽，避免测试因为第三方表格内部实现而丢失业务可见文本。
 */
const tableRowsKey: InjectionKey<unknown[]> = Symbol("frontend-test-table-rows");

export const elementTableStubs: Record<string, Component> = {
  "el-table": {
    props: { data: { type: Array, default: () => [] } },
    setup(props, { slots }) {
      provide(tableRowsKey, props.data as unknown[]);
      return () => h("div", { class: "table" }, slots.default?.());
    },
  },
  "el-table-column": {
    props: { label: String, prop: String },
    setup(props, { slots }) {
      const rows = inject(tableRowsKey, []);
      return () => h("div", { class: "table-column" }, [
        props.label ? h("span", { class: "column-label" }, props.label) : null,
        ...rows.map((row) => {
          if (slots.default) return slots.default({ row });
          if (!props.prop) return null;
          const value = (row as Record<string, unknown>)?.[props.prop];
          return h("span", { class: "cell" }, value == null ? "" : String(value));
        }),
      ]);
    },
  },
};
