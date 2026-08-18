import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { runtimeApi } from "../api/runtime";
const items = ref([]), events = ref([]), selected = ref();
const page = ref(1), pageSize = ref(20), total = ref(0), status = ref(""), loading = ref(false), error = ref(false), drawer = ref(false), detailError = ref(false);
async function load() { loading.value = true; error.value = false; try {
    const r = await runtimeApi.executions({ page: page.value, page_size: pageSize.value, ...(status.value ? { status: status.value } : {}) });
    items.value = r.data.items;
    total.value = r.data.total;
}
catch {
    error.value = true;
    ElMessage.error("Runtime 查询失败");
}
finally {
    loading.value = false;
} }
async function open(row) { selected.value = row; events.value = []; detailError.value = false; drawer.value = true; try {
    events.value = (await runtimeApi.executionEvents(row.execution_id)).data.items;
}
catch {
    detailError.value = true;
    ElMessage.error("Execution Timeline 查询失败");
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
__VLS_3.slots.default;
{
    const { header: __VLS_thisSlot } = __VLS_3.slots;
}
const __VLS_4 = {}.ElForm;
/** @type {[typeof __VLS_components.ElForm, typeof __VLS_components.elForm, typeof __VLS_components.ElForm, typeof __VLS_components.elForm, ]} */ ;
// @ts-ignore
const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
    ...{ 'onSubmit': {} },
    inline: true,
}));
const __VLS_6 = __VLS_5({
    ...{ 'onSubmit': {} },
    inline: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_5));
let __VLS_8;
let __VLS_9;
let __VLS_10;
const __VLS_11 = {
    onSubmit: () => { }
};
__VLS_7.slots.default;
const __VLS_12 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
    ...{ 'onKeyup': {} },
    modelValue: (__VLS_ctx.status),
    placeholder: "Status",
    clearable: true,
}));
const __VLS_14 = __VLS_13({
    ...{ 'onKeyup': {} },
    modelValue: (__VLS_ctx.status),
    placeholder: "Status",
    clearable: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_13));
let __VLS_16;
let __VLS_17;
let __VLS_18;
const __VLS_19 = {
    onKeyup: (__VLS_ctx.load)
};
var __VLS_15;
const __VLS_20 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
    ...{ 'onClick': {} },
    type: "primary",
}));
const __VLS_22 = __VLS_21({
    ...{ 'onClick': {} },
    type: "primary",
}, ...__VLS_functionalComponentArgsRest(__VLS_21));
let __VLS_24;
let __VLS_25;
let __VLS_26;
const __VLS_27 = {
    onClick: (__VLS_ctx.load)
};
__VLS_23.slots.default;
var __VLS_23;
var __VLS_7;
if (__VLS_ctx.error) {
    const __VLS_28 = {}.ElAlert;
    /** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
    // @ts-ignore
    const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
        type: "error",
        closable: (false),
        title: "Runtime 查询失败，请稍后重试",
    }));
    const __VLS_30 = __VLS_29({
        type: "error",
        closable: (false),
        title: "Runtime 查询失败，请稍后重试",
    }, ...__VLS_functionalComponentArgsRest(__VLS_29));
}
else if (!__VLS_ctx.loading && __VLS_ctx.items.length === 0) {
    const __VLS_32 = {}.ElEmpty;
    /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
    // @ts-ignore
    const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
        description: "暂无 Runtime Execution",
    }));
    const __VLS_34 = __VLS_33({
        description: "暂无 Runtime Execution",
    }, ...__VLS_functionalComponentArgsRest(__VLS_33));
}
else {
    const __VLS_36 = {}.ElTable;
    /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
    // @ts-ignore
    const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
        ...{ 'onRowClick': {} },
        data: (__VLS_ctx.items),
    }));
    const __VLS_38 = __VLS_37({
        ...{ 'onRowClick': {} },
        data: (__VLS_ctx.items),
    }, ...__VLS_functionalComponentArgsRest(__VLS_37));
    let __VLS_40;
    let __VLS_41;
    let __VLS_42;
    const __VLS_43 = {
        onRowClick: (__VLS_ctx.open)
    };
    __VLS_asFunctionalDirective(__VLS_directives.vLoading)(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.loading) }, null, null);
    __VLS_39.slots.default;
    const __VLS_44 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_45 = __VLS_asFunctionalComponent(__VLS_44, new __VLS_44({
        prop: "execution_id",
        label: "Execution",
        minWidth: "260",
    }));
    const __VLS_46 = __VLS_45({
        prop: "execution_id",
        label: "Execution",
        minWidth: "260",
    }, ...__VLS_functionalComponentArgsRest(__VLS_45));
    const __VLS_48 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_49 = __VLS_asFunctionalComponent(__VLS_48, new __VLS_48({
        prop: "status",
        label: "Status",
        width: "120",
    }));
    const __VLS_50 = __VLS_49({
        prop: "status",
        label: "Status",
        width: "120",
    }, ...__VLS_functionalComponentArgsRest(__VLS_49));
    const __VLS_52 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_53 = __VLS_asFunctionalComponent(__VLS_52, new __VLS_52({
        prop: "agent_id",
        label: "Agent",
        minWidth: "220",
    }));
    const __VLS_54 = __VLS_53({
        prop: "agent_id",
        label: "Agent",
        minWidth: "220",
    }, ...__VLS_functionalComponentArgsRest(__VLS_53));
    const __VLS_56 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_57 = __VLS_asFunctionalComponent(__VLS_56, new __VLS_56({
        prop: "trace_id",
        label: "Trace",
        minWidth: "220",
    }));
    const __VLS_58 = __VLS_57({
        prop: "trace_id",
        label: "Trace",
        minWidth: "220",
    }, ...__VLS_functionalComponentArgsRest(__VLS_57));
    const __VLS_60 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_61 = __VLS_asFunctionalComponent(__VLS_60, new __VLS_60({
        prop: "started_at",
        label: "Started",
        minWidth: "190",
    }));
    const __VLS_62 = __VLS_61({
        prop: "started_at",
        label: "Started",
        minWidth: "190",
    }, ...__VLS_functionalComponentArgsRest(__VLS_61));
    var __VLS_39;
}
if (__VLS_ctx.total) {
    const __VLS_64 = {}.ElPagination;
    /** @type {[typeof __VLS_components.ElPagination, typeof __VLS_components.elPagination, ]} */ ;
    // @ts-ignore
    const __VLS_65 = __VLS_asFunctionalComponent(__VLS_64, new __VLS_64({
        ...{ 'onChange': {} },
        currentPage: (__VLS_ctx.page),
        pageSize: (__VLS_ctx.pageSize),
        total: (__VLS_ctx.total),
        pageSizes: ([10, 20, 50, 100]),
        layout: "total, sizes, prev, pager, next",
    }));
    const __VLS_66 = __VLS_65({
        ...{ 'onChange': {} },
        currentPage: (__VLS_ctx.page),
        pageSize: (__VLS_ctx.pageSize),
        total: (__VLS_ctx.total),
        pageSizes: ([10, 20, 50, 100]),
        layout: "total, sizes, prev, pager, next",
    }, ...__VLS_functionalComponentArgsRest(__VLS_65));
    let __VLS_68;
    let __VLS_69;
    let __VLS_70;
    const __VLS_71 = {
        onChange: (__VLS_ctx.load)
    };
    var __VLS_67;
}
var __VLS_3;
const __VLS_72 = {}.ElDrawer;
/** @type {[typeof __VLS_components.ElDrawer, typeof __VLS_components.elDrawer, typeof __VLS_components.ElDrawer, typeof __VLS_components.elDrawer, ]} */ ;
// @ts-ignore
const __VLS_73 = __VLS_asFunctionalComponent(__VLS_72, new __VLS_72({
    modelValue: (__VLS_ctx.drawer),
    title: "Execution Timeline",
    size: "55%",
}));
const __VLS_74 = __VLS_73({
    modelValue: (__VLS_ctx.drawer),
    title: "Execution Timeline",
    size: "55%",
}, ...__VLS_functionalComponentArgsRest(__VLS_73));
__VLS_75.slots.default;
if (__VLS_ctx.detailError) {
    const __VLS_76 = {}.ElAlert;
    /** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
    // @ts-ignore
    const __VLS_77 = __VLS_asFunctionalComponent(__VLS_76, new __VLS_76({
        type: "error",
        closable: (false),
        title: "Timeline 查询失败",
    }));
    const __VLS_78 = __VLS_77({
        type: "error",
        closable: (false),
        title: "Timeline 查询失败",
    }, ...__VLS_functionalComponentArgsRest(__VLS_77));
}
else {
    if (__VLS_ctx.selected) {
        const __VLS_80 = {}.ElDescriptions;
        /** @type {[typeof __VLS_components.ElDescriptions, typeof __VLS_components.elDescriptions, typeof __VLS_components.ElDescriptions, typeof __VLS_components.elDescriptions, ]} */ ;
        // @ts-ignore
        const __VLS_81 = __VLS_asFunctionalComponent(__VLS_80, new __VLS_80({
            column: (2),
            border: true,
        }));
        const __VLS_82 = __VLS_81({
            column: (2),
            border: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_81));
        __VLS_83.slots.default;
        const __VLS_84 = {}.ElDescriptionsItem;
        /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
        // @ts-ignore
        const __VLS_85 = __VLS_asFunctionalComponent(__VLS_84, new __VLS_84({
            label: "Execution",
        }));
        const __VLS_86 = __VLS_85({
            label: "Execution",
        }, ...__VLS_functionalComponentArgsRest(__VLS_85));
        __VLS_87.slots.default;
        (__VLS_ctx.selected.execution_id);
        var __VLS_87;
        const __VLS_88 = {}.ElDescriptionsItem;
        /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
        // @ts-ignore
        const __VLS_89 = __VLS_asFunctionalComponent(__VLS_88, new __VLS_88({
            label: "Status",
        }));
        const __VLS_90 = __VLS_89({
            label: "Status",
        }, ...__VLS_functionalComponentArgsRest(__VLS_89));
        __VLS_91.slots.default;
        (__VLS_ctx.selected.status);
        var __VLS_91;
        const __VLS_92 = {}.ElDescriptionsItem;
        /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
        // @ts-ignore
        const __VLS_93 = __VLS_asFunctionalComponent(__VLS_92, new __VLS_92({
            label: "Trace",
        }));
        const __VLS_94 = __VLS_93({
            label: "Trace",
        }, ...__VLS_functionalComponentArgsRest(__VLS_93));
        __VLS_95.slots.default;
        (__VLS_ctx.selected.trace_id);
        var __VLS_95;
        const __VLS_96 = {}.ElDescriptionsItem;
        /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
        // @ts-ignore
        const __VLS_97 = __VLS_asFunctionalComponent(__VLS_96, new __VLS_96({
            label: "Request",
        }));
        const __VLS_98 = __VLS_97({
            label: "Request",
        }, ...__VLS_functionalComponentArgsRest(__VLS_97));
        __VLS_99.slots.default;
        (__VLS_ctx.selected.request_id);
        var __VLS_99;
        var __VLS_83;
    }
    if (!__VLS_ctx.events.length) {
        const __VLS_100 = {}.ElEmpty;
        /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
        // @ts-ignore
        const __VLS_101 = __VLS_asFunctionalComponent(__VLS_100, new __VLS_100({
            description: "暂无 Timeline Event",
        }));
        const __VLS_102 = __VLS_101({
            description: "暂无 Timeline Event",
        }, ...__VLS_functionalComponentArgsRest(__VLS_101));
    }
    else {
        const __VLS_104 = {}.ElTimeline;
        /** @type {[typeof __VLS_components.ElTimeline, typeof __VLS_components.elTimeline, typeof __VLS_components.ElTimeline, typeof __VLS_components.elTimeline, ]} */ ;
        // @ts-ignore
        const __VLS_105 = __VLS_asFunctionalComponent(__VLS_104, new __VLS_104({}));
        const __VLS_106 = __VLS_105({}, ...__VLS_functionalComponentArgsRest(__VLS_105));
        __VLS_107.slots.default;
        for (const [event] of __VLS_getVForSourceType((__VLS_ctx.events))) {
            const __VLS_108 = {}.ElTimelineItem;
            /** @type {[typeof __VLS_components.ElTimelineItem, typeof __VLS_components.elTimelineItem, typeof __VLS_components.ElTimelineItem, typeof __VLS_components.elTimelineItem, ]} */ ;
            // @ts-ignore
            const __VLS_109 = __VLS_asFunctionalComponent(__VLS_108, new __VLS_108({
                key: (event.id),
                timestamp: (event.started_at),
            }));
            const __VLS_110 = __VLS_109({
                key: (event.id),
                timestamp: (event.started_at),
            }, ...__VLS_functionalComponentArgsRest(__VLS_109));
            __VLS_111.slots.default;
            (event.span_type);
            (event.status);
            (event.duration_ms ?? 0);
            var __VLS_111;
        }
        var __VLS_107;
    }
}
var __VLS_75;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            items: items,
            events: events,
            selected: selected,
            page: page,
            pageSize: pageSize,
            total: total,
            status: status,
            loading: loading,
            error: error,
            drawer: drawer,
            detailError: detailError,
            load: load,
            open: open,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
