import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { runtimeApi } from "../api/runtime";
const items = ref([]), page = ref(1), pageSize = ref(20), total = ref(0), status = ref(""), loading = ref(false), error = ref(false);
async function load() { loading.value = true; error.value = false; try {
    const r = await runtimeApi.auditLogs({ page: page.value, page_size: pageSize.value, ...(status.value ? { status: status.value } : {}) });
    items.value = r.data.items;
    total.value = r.data.total;
}
catch {
    error.value = true;
    ElMessage.error("Audit 查询失败");
}
finally {
    loading.value = false;
} }
onMounted(load);
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
const __VLS_0 = {}.ElCard;
/** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({}));
const __VLS_2 = __VLS_1({}, ...__VLS_functionalComponentArgsRest(__VLS_1));
var __VLS_4 = {};
__VLS_3.slots.default;
{
    const { header: __VLS_thisSlot } = __VLS_3.slots;
}
const __VLS_5 = {}.ElForm;
/** @type {[typeof __VLS_components.ElForm, typeof __VLS_components.elForm, typeof __VLS_components.ElForm, typeof __VLS_components.elForm, ]} */ ;
// @ts-ignore
const __VLS_6 = __VLS_asFunctionalComponent(__VLS_5, new __VLS_5({
    ...{ 'onSubmit': {} },
    inline: true,
}));
const __VLS_7 = __VLS_6({
    ...{ 'onSubmit': {} },
    inline: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_6));
let __VLS_9;
let __VLS_10;
let __VLS_11;
const __VLS_12 = {
    onSubmit: (__VLS_ctx.load)
};
__VLS_8.slots.default;
const __VLS_13 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
const __VLS_14 = __VLS_asFunctionalComponent(__VLS_13, new __VLS_13({
    modelValue: (__VLS_ctx.status),
    placeholder: "Status",
    clearable: true,
}));
const __VLS_15 = __VLS_14({
    modelValue: (__VLS_ctx.status),
    placeholder: "Status",
    clearable: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_14));
const __VLS_17 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
const __VLS_18 = __VLS_asFunctionalComponent(__VLS_17, new __VLS_17({
    ...{ 'onClick': {} },
    type: "primary",
}));
const __VLS_19 = __VLS_18({
    ...{ 'onClick': {} },
    type: "primary",
}, ...__VLS_functionalComponentArgsRest(__VLS_18));
let __VLS_21;
let __VLS_22;
let __VLS_23;
const __VLS_24 = {
    onClick: (__VLS_ctx.load)
};
__VLS_20.slots.default;
var __VLS_20;
var __VLS_8;
if (__VLS_ctx.error) {
    const __VLS_25 = {}.ElAlert;
    /** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
    // @ts-ignore
    const __VLS_26 = __VLS_asFunctionalComponent(__VLS_25, new __VLS_25({
        type: "error",
        closable: (false),
        title: "Audit 查询失败",
    }));
    const __VLS_27 = __VLS_26({
        type: "error",
        closable: (false),
        title: "Audit 查询失败",
    }, ...__VLS_functionalComponentArgsRest(__VLS_26));
}
else if (!__VLS_ctx.loading && !__VLS_ctx.items.length) {
    const __VLS_29 = {}.ElEmpty;
    /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
    // @ts-ignore
    const __VLS_30 = __VLS_asFunctionalComponent(__VLS_29, new __VLS_29({
        description: "暂无 Audit Log",
    }));
    const __VLS_31 = __VLS_30({
        description: "暂无 Audit Log",
    }, ...__VLS_functionalComponentArgsRest(__VLS_30));
}
else {
    const __VLS_33 = {}.ElTable;
    /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
    // @ts-ignore
    const __VLS_34 = __VLS_asFunctionalComponent(__VLS_33, new __VLS_33({
        data: (__VLS_ctx.items),
    }));
    const __VLS_35 = __VLS_34({
        data: (__VLS_ctx.items),
    }, ...__VLS_functionalComponentArgsRest(__VLS_34));
    __VLS_asFunctionalDirective(__VLS_directives.vLoading)(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.loading) }, null, null);
    __VLS_36.slots.default;
    const __VLS_37 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_38 = __VLS_asFunctionalComponent(__VLS_37, new __VLS_37({
        prop: "id",
        label: "ID",
        minWidth: "260",
    }));
    const __VLS_39 = __VLS_38({
        prop: "id",
        label: "ID",
        minWidth: "260",
    }, ...__VLS_functionalComponentArgsRest(__VLS_38));
    const __VLS_41 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_42 = __VLS_asFunctionalComponent(__VLS_41, new __VLS_41({
        prop: "action",
        label: "Action",
    }));
    const __VLS_43 = __VLS_42({
        prop: "action",
        label: "Action",
    }, ...__VLS_functionalComponentArgsRest(__VLS_42));
    const __VLS_45 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_46 = __VLS_asFunctionalComponent(__VLS_45, new __VLS_45({
        prop: "status",
        label: "Status",
    }));
    const __VLS_47 = __VLS_46({
        prop: "status",
        label: "Status",
    }, ...__VLS_functionalComponentArgsRest(__VLS_46));
    const __VLS_49 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_50 = __VLS_asFunctionalComponent(__VLS_49, new __VLS_49({
        prop: "agent_id",
        label: "Agent",
        minWidth: "220",
    }));
    const __VLS_51 = __VLS_50({
        prop: "agent_id",
        label: "Agent",
        minWidth: "220",
    }, ...__VLS_functionalComponentArgsRest(__VLS_50));
    const __VLS_53 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_54 = __VLS_asFunctionalComponent(__VLS_53, new __VLS_53({
        prop: "tool_id",
        label: "Tool",
        minWidth: "220",
    }));
    const __VLS_55 = __VLS_54({
        prop: "tool_id",
        label: "Tool",
        minWidth: "220",
    }, ...__VLS_functionalComponentArgsRest(__VLS_54));
    const __VLS_57 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_58 = __VLS_asFunctionalComponent(__VLS_57, new __VLS_57({
        prop: "created_at",
        label: "Created At",
    }));
    const __VLS_59 = __VLS_58({
        prop: "created_at",
        label: "Created At",
    }, ...__VLS_functionalComponentArgsRest(__VLS_58));
    var __VLS_36;
}
if (__VLS_ctx.total) {
    const __VLS_61 = {}.ElPagination;
    /** @type {[typeof __VLS_components.ElPagination, typeof __VLS_components.elPagination, ]} */ ;
    // @ts-ignore
    const __VLS_62 = __VLS_asFunctionalComponent(__VLS_61, new __VLS_61({
        ...{ 'onChange': {} },
        currentPage: (__VLS_ctx.page),
        pageSize: (__VLS_ctx.pageSize),
        total: (__VLS_ctx.total),
        pageSizes: ([10, 20, 50, 100]),
        layout: "total, sizes, prev, pager, next",
    }));
    const __VLS_63 = __VLS_62({
        ...{ 'onChange': {} },
        currentPage: (__VLS_ctx.page),
        pageSize: (__VLS_ctx.pageSize),
        total: (__VLS_ctx.total),
        pageSizes: ([10, 20, 50, 100]),
        layout: "total, sizes, prev, pager, next",
    }, ...__VLS_functionalComponentArgsRest(__VLS_62));
    let __VLS_65;
    let __VLS_66;
    let __VLS_67;
    const __VLS_68 = {
        onChange: (__VLS_ctx.load)
    };
    var __VLS_64;
}
var __VLS_3;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            items: items,
            page: page,
            pageSize: pageSize,
            total: total,
            status: status,
            loading: loading,
            error: error,
            load: load,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
