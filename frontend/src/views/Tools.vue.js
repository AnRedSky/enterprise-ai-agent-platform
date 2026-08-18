import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { getRoles } from "../api/auth";
import { listAgents } from "../api/agents";
import { bindTool, createTool, disableTool, enableTool, executeTool, listTools, unbindTool } from "../api/tools";
const tools = ref([]);
const agents = ref([]);
const loading = ref(false);
const saving = ref(false);
const executing = ref(false);
const error = ref("");
const createVisible = ref(false);
const bindVisible = ref(false);
const executeVisible = ref(false);
const selectedTool = ref(null);
const selectedAgent = ref("");
const bindingAction = ref("bind");
const argumentsText = ref("{}\n");
const executionResult = ref("");
const createForm = ref({ name: "", description: "", endpoint: "", input_schema: "{}" });
const isAdmin = computed(() => getRoles().includes("admin"));
async function load() {
    loading.value = true;
    try {
        [tools.value, agents.value] = await Promise.all([listTools(), listAgents()]);
    }
    catch (e) {
        error.value = e instanceof Error ? e.message : "Tool 数据加载失败";
    }
    finally {
        loading.value = false;
    }
}
async function toggle(tool) {
    try {
        await (tool.enabled ? disableTool(tool.id) : enableTool(tool.id));
        await load();
        ElMessage.success(tool.enabled ? "Tool 已停用" : "Tool 已启用");
    }
    catch (e) {
        ElMessage.error(e instanceof Error ? e.message : "Tool 状态更新失败");
    }
}
async function create() {
    try {
        const input_schema = JSON.parse(createForm.value.input_schema || "{}");
        saving.value = true;
        await createTool({ ...createForm.value, input_schema, enabled: true });
        createVisible.value = false;
        await load();
        ElMessage.success("Tool 创建成功");
    }
    catch (e) {
        ElMessage.error(e instanceof Error ? e.message : "Tool 创建失败，请检查 JSON Schema");
    }
    finally {
        saving.value = false;
    }
}
function openBind(tool, action) {
    selectedTool.value = tool;
    bindingAction.value = action;
    selectedAgent.value = agents.value[0]?.id || "";
    bindVisible.value = true;
}
async function applyBinding() {
    if (!selectedTool.value || !selectedAgent.value)
        return;
    saving.value = true;
    try {
        if (bindingAction.value === "bind") {
            await bindTool(selectedTool.value.id, selectedAgent.value);
            ElMessage.success("Tool 绑定成功");
        }
        else {
            await unbindTool(selectedTool.value.id, selectedAgent.value);
            ElMessage.success("Tool 解绑成功");
        }
        bindVisible.value = false;
    }
    catch (e) {
        ElMessage.error(e instanceof Error ? e.message : "Tool 绑定关系更新失败");
    }
    finally {
        saving.value = false;
    }
}
function openExecute(tool) {
    selectedTool.value = tool;
    selectedAgent.value = agents.value[0]?.id || "";
    argumentsText.value = "{}\n";
    executionResult.value = "";
    executeVisible.value = true;
}
async function execute() {
    if (!selectedTool.value || !selectedAgent.value) {
        ElMessage.warning("请选择 Agent");
        return;
    }
    try {
        executing.value = true;
        const result = await executeTool(selectedTool.value.id, selectedAgent.value, JSON.parse(argumentsText.value || "{}"));
        executionResult.value = JSON.stringify(result, null, 2);
    }
    catch (e) {
        executionResult.value = e instanceof Error ? e.message : "Tool 执行失败";
        ElMessage.error("Tool 执行失败");
    }
    finally {
        executing.value = false;
    }
}
onMounted(load);
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['header']} */ ;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "page" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "header" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h1, __VLS_intrinsicElements.h1)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
if (__VLS_ctx.isAdmin) {
    const __VLS_0 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
        ...{ 'onClick': {} },
        type: "primary",
    }));
    const __VLS_2 = __VLS_1({
        ...{ 'onClick': {} },
        type: "primary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    let __VLS_4;
    let __VLS_5;
    let __VLS_6;
    const __VLS_7 = {
        onClick: (...[$event]) => {
            if (!(__VLS_ctx.isAdmin))
                return;
            __VLS_ctx.createVisible = true;
        }
    };
    __VLS_3.slots.default;
    var __VLS_3;
}
if (__VLS_ctx.error) {
    const __VLS_8 = {}.ElAlert;
    /** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
    // @ts-ignore
    const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
        ...{ 'onClose': {} },
        title: (__VLS_ctx.error),
        type: "error",
        showIcon: true,
        closable: true,
    }));
    const __VLS_10 = __VLS_9({
        ...{ 'onClose': {} },
        title: (__VLS_ctx.error),
        type: "error",
        showIcon: true,
        closable: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_9));
    let __VLS_12;
    let __VLS_13;
    let __VLS_14;
    const __VLS_15 = {
        onClose: (...[$event]) => {
            if (!(__VLS_ctx.error))
                return;
            __VLS_ctx.error = '';
        }
    };
    var __VLS_11;
}
const __VLS_16 = {}.ElTable;
/** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
    data: (__VLS_ctx.tools),
    border: true,
    ...{ class: "table" },
}));
const __VLS_18 = __VLS_17({
    data: (__VLS_ctx.tools),
    border: true,
    ...{ class: "table" },
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
__VLS_asFunctionalDirective(__VLS_directives.vLoading)(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.loading) }, null, null);
__VLS_19.slots.default;
const __VLS_20 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
    prop: "name",
    label: "名称",
    minWidth: "180",
}));
const __VLS_22 = __VLS_21({
    prop: "name",
    label: "名称",
    minWidth: "180",
}, ...__VLS_functionalComponentArgsRest(__VLS_21));
const __VLS_24 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
    prop: "description",
    label: "描述",
    minWidth: "220",
}));
const __VLS_26 = __VLS_25({
    prop: "description",
    label: "描述",
    minWidth: "220",
}, ...__VLS_functionalComponentArgsRest(__VLS_25));
const __VLS_28 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
    label: "状态",
    width: "110",
}));
const __VLS_30 = __VLS_29({
    label: "状态",
    width: "110",
}, ...__VLS_functionalComponentArgsRest(__VLS_29));
__VLS_31.slots.default;
{
    const { default: __VLS_thisSlot } = __VLS_31.slots;
    const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
    const __VLS_32 = {}.ElTag;
    /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
    // @ts-ignore
    const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
        type: (row.enabled ? 'success' : 'info'),
    }));
    const __VLS_34 = __VLS_33({
        type: (row.enabled ? 'success' : 'info'),
    }, ...__VLS_functionalComponentArgsRest(__VLS_33));
    __VLS_35.slots.default;
    (row.enabled ? '启用' : '停用');
    var __VLS_35;
}
var __VLS_31;
const __VLS_36 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
    label: "操作",
    width: "420",
}));
const __VLS_38 = __VLS_37({
    label: "操作",
    width: "420",
}, ...__VLS_functionalComponentArgsRest(__VLS_37));
__VLS_39.slots.default;
{
    const { default: __VLS_thisSlot } = __VLS_39.slots;
    const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
    if (__VLS_ctx.isAdmin) {
        const __VLS_40 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        const __VLS_41 = __VLS_asFunctionalComponent(__VLS_40, new __VLS_40({
            ...{ 'onClick': {} },
            link: true,
            type: "primary",
        }));
        const __VLS_42 = __VLS_41({
            ...{ 'onClick': {} },
            link: true,
            type: "primary",
        }, ...__VLS_functionalComponentArgsRest(__VLS_41));
        let __VLS_44;
        let __VLS_45;
        let __VLS_46;
        const __VLS_47 = {
            onClick: (...[$event]) => {
                if (!(__VLS_ctx.isAdmin))
                    return;
                __VLS_ctx.toggle(row);
            }
        };
        __VLS_43.slots.default;
        (row.enabled ? '停用' : '启用');
        var __VLS_43;
    }
    const __VLS_48 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_49 = __VLS_asFunctionalComponent(__VLS_48, new __VLS_48({
        ...{ 'onClick': {} },
        link: true,
        type: "primary",
    }));
    const __VLS_50 = __VLS_49({
        ...{ 'onClick': {} },
        link: true,
        type: "primary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_49));
    let __VLS_52;
    let __VLS_53;
    let __VLS_54;
    const __VLS_55 = {
        onClick: (...[$event]) => {
            __VLS_ctx.openExecute(row);
        }
    };
    __VLS_51.slots.default;
    var __VLS_51;
    if (__VLS_ctx.isAdmin) {
        const __VLS_56 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        const __VLS_57 = __VLS_asFunctionalComponent(__VLS_56, new __VLS_56({
            ...{ 'onClick': {} },
            link: true,
            type: "primary",
        }));
        const __VLS_58 = __VLS_57({
            ...{ 'onClick': {} },
            link: true,
            type: "primary",
        }, ...__VLS_functionalComponentArgsRest(__VLS_57));
        let __VLS_60;
        let __VLS_61;
        let __VLS_62;
        const __VLS_63 = {
            onClick: (...[$event]) => {
                if (!(__VLS_ctx.isAdmin))
                    return;
                __VLS_ctx.openBind(row, 'bind');
            }
        };
        __VLS_59.slots.default;
        var __VLS_59;
    }
    if (__VLS_ctx.isAdmin) {
        const __VLS_64 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        const __VLS_65 = __VLS_asFunctionalComponent(__VLS_64, new __VLS_64({
            ...{ 'onClick': {} },
            link: true,
            type: "danger",
        }));
        const __VLS_66 = __VLS_65({
            ...{ 'onClick': {} },
            link: true,
            type: "danger",
        }, ...__VLS_functionalComponentArgsRest(__VLS_65));
        let __VLS_68;
        let __VLS_69;
        let __VLS_70;
        const __VLS_71 = {
            onClick: (...[$event]) => {
                if (!(__VLS_ctx.isAdmin))
                    return;
                __VLS_ctx.openBind(row, 'unbind');
            }
        };
        __VLS_67.slots.default;
        var __VLS_67;
    }
}
var __VLS_39;
var __VLS_19;
if (!__VLS_ctx.loading && !__VLS_ctx.tools.length) {
    const __VLS_72 = {}.ElEmpty;
    /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
    // @ts-ignore
    const __VLS_73 = __VLS_asFunctionalComponent(__VLS_72, new __VLS_72({
        description: "暂无可用 Tool。",
    }));
    const __VLS_74 = __VLS_73({
        description: "暂无可用 Tool。",
    }, ...__VLS_functionalComponentArgsRest(__VLS_73));
}
const __VLS_76 = {}.ElDialog;
/** @type {[typeof __VLS_components.ElDialog, typeof __VLS_components.elDialog, typeof __VLS_components.ElDialog, typeof __VLS_components.elDialog, ]} */ ;
// @ts-ignore
const __VLS_77 = __VLS_asFunctionalComponent(__VLS_76, new __VLS_76({
    modelValue: (__VLS_ctx.createVisible),
    title: "创建 Tool",
    width: "620px",
}));
const __VLS_78 = __VLS_77({
    modelValue: (__VLS_ctx.createVisible),
    title: "创建 Tool",
    width: "620px",
}, ...__VLS_functionalComponentArgsRest(__VLS_77));
__VLS_79.slots.default;
const __VLS_80 = {}.ElForm;
/** @type {[typeof __VLS_components.ElForm, typeof __VLS_components.elForm, typeof __VLS_components.ElForm, typeof __VLS_components.elForm, ]} */ ;
// @ts-ignore
const __VLS_81 = __VLS_asFunctionalComponent(__VLS_80, new __VLS_80({
    labelWidth: "110px",
}));
const __VLS_82 = __VLS_81({
    labelWidth: "110px",
}, ...__VLS_functionalComponentArgsRest(__VLS_81));
__VLS_83.slots.default;
const __VLS_84 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_85 = __VLS_asFunctionalComponent(__VLS_84, new __VLS_84({
    label: "名称",
    required: true,
}));
const __VLS_86 = __VLS_85({
    label: "名称",
    required: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_85));
__VLS_87.slots.default;
const __VLS_88 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
const __VLS_89 = __VLS_asFunctionalComponent(__VLS_88, new __VLS_88({
    modelValue: (__VLS_ctx.createForm.name),
}));
const __VLS_90 = __VLS_89({
    modelValue: (__VLS_ctx.createForm.name),
}, ...__VLS_functionalComponentArgsRest(__VLS_89));
var __VLS_87;
const __VLS_92 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_93 = __VLS_asFunctionalComponent(__VLS_92, new __VLS_92({
    label: "描述",
}));
const __VLS_94 = __VLS_93({
    label: "描述",
}, ...__VLS_functionalComponentArgsRest(__VLS_93));
__VLS_95.slots.default;
const __VLS_96 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
const __VLS_97 = __VLS_asFunctionalComponent(__VLS_96, new __VLS_96({
    modelValue: (__VLS_ctx.createForm.description),
}));
const __VLS_98 = __VLS_97({
    modelValue: (__VLS_ctx.createForm.description),
}, ...__VLS_functionalComponentArgsRest(__VLS_97));
var __VLS_95;
const __VLS_100 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_101 = __VLS_asFunctionalComponent(__VLS_100, new __VLS_100({
    label: "Endpoint",
}));
const __VLS_102 = __VLS_101({
    label: "Endpoint",
}, ...__VLS_functionalComponentArgsRest(__VLS_101));
__VLS_103.slots.default;
const __VLS_104 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
const __VLS_105 = __VLS_asFunctionalComponent(__VLS_104, new __VLS_104({
    modelValue: (__VLS_ctx.createForm.endpoint),
    placeholder: "可选；禁止未经授权的 URL 执行",
}));
const __VLS_106 = __VLS_105({
    modelValue: (__VLS_ctx.createForm.endpoint),
    placeholder: "可选；禁止未经授权的 URL 执行",
}, ...__VLS_functionalComponentArgsRest(__VLS_105));
var __VLS_103;
const __VLS_108 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_109 = __VLS_asFunctionalComponent(__VLS_108, new __VLS_108({
    label: "Input Schema",
}));
const __VLS_110 = __VLS_109({
    label: "Input Schema",
}, ...__VLS_functionalComponentArgsRest(__VLS_109));
__VLS_111.slots.default;
const __VLS_112 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
const __VLS_113 = __VLS_asFunctionalComponent(__VLS_112, new __VLS_112({
    modelValue: (__VLS_ctx.createForm.input_schema),
    type: "textarea",
    rows: (8),
}));
const __VLS_114 = __VLS_113({
    modelValue: (__VLS_ctx.createForm.input_schema),
    type: "textarea",
    rows: (8),
}, ...__VLS_functionalComponentArgsRest(__VLS_113));
var __VLS_111;
var __VLS_83;
{
    const { footer: __VLS_thisSlot } = __VLS_79.slots;
    const __VLS_116 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_117 = __VLS_asFunctionalComponent(__VLS_116, new __VLS_116({
        ...{ 'onClick': {} },
    }));
    const __VLS_118 = __VLS_117({
        ...{ 'onClick': {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_117));
    let __VLS_120;
    let __VLS_121;
    let __VLS_122;
    const __VLS_123 = {
        onClick: (...[$event]) => {
            __VLS_ctx.createVisible = false;
        }
    };
    __VLS_119.slots.default;
    var __VLS_119;
    const __VLS_124 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_125 = __VLS_asFunctionalComponent(__VLS_124, new __VLS_124({
        ...{ 'onClick': {} },
        type: "primary",
        loading: (__VLS_ctx.saving),
    }));
    const __VLS_126 = __VLS_125({
        ...{ 'onClick': {} },
        type: "primary",
        loading: (__VLS_ctx.saving),
    }, ...__VLS_functionalComponentArgsRest(__VLS_125));
    let __VLS_128;
    let __VLS_129;
    let __VLS_130;
    const __VLS_131 = {
        onClick: (__VLS_ctx.create)
    };
    __VLS_127.slots.default;
    var __VLS_127;
}
var __VLS_79;
const __VLS_132 = {}.ElDialog;
/** @type {[typeof __VLS_components.ElDialog, typeof __VLS_components.elDialog, typeof __VLS_components.ElDialog, typeof __VLS_components.elDialog, ]} */ ;
// @ts-ignore
const __VLS_133 = __VLS_asFunctionalComponent(__VLS_132, new __VLS_132({
    modelValue: (__VLS_ctx.bindVisible),
    title: (__VLS_ctx.bindingAction === 'bind' ? '绑定 Tool 到 Agent' : '解绑 Tool 到 Agent'),
    width: "520px",
}));
const __VLS_134 = __VLS_133({
    modelValue: (__VLS_ctx.bindVisible),
    title: (__VLS_ctx.bindingAction === 'bind' ? '绑定 Tool 到 Agent' : '解绑 Tool 到 Agent'),
    width: "520px",
}, ...__VLS_functionalComponentArgsRest(__VLS_133));
__VLS_135.slots.default;
const __VLS_136 = {}.ElSelect;
/** @type {[typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, ]} */ ;
// @ts-ignore
const __VLS_137 = __VLS_asFunctionalComponent(__VLS_136, new __VLS_136({
    modelValue: (__VLS_ctx.selectedAgent),
    placeholder: "选择 Agent",
    ...{ style: {} },
}));
const __VLS_138 = __VLS_137({
    modelValue: (__VLS_ctx.selectedAgent),
    placeholder: "选择 Agent",
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_137));
__VLS_139.slots.default;
for (const [agent] of __VLS_getVForSourceType((__VLS_ctx.agents))) {
    const __VLS_140 = {}.ElOption;
    /** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
    // @ts-ignore
    const __VLS_141 = __VLS_asFunctionalComponent(__VLS_140, new __VLS_140({
        key: (agent.id),
        label: (agent.name),
        value: (agent.id),
    }));
    const __VLS_142 = __VLS_141({
        key: (agent.id),
        label: (agent.name),
        value: (agent.id),
    }, ...__VLS_functionalComponentArgsRest(__VLS_141));
}
var __VLS_139;
{
    const { footer: __VLS_thisSlot } = __VLS_135.slots;
    const __VLS_144 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_145 = __VLS_asFunctionalComponent(__VLS_144, new __VLS_144({
        ...{ 'onClick': {} },
    }));
    const __VLS_146 = __VLS_145({
        ...{ 'onClick': {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_145));
    let __VLS_148;
    let __VLS_149;
    let __VLS_150;
    const __VLS_151 = {
        onClick: (...[$event]) => {
            __VLS_ctx.bindVisible = false;
        }
    };
    __VLS_147.slots.default;
    var __VLS_147;
    const __VLS_152 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_153 = __VLS_asFunctionalComponent(__VLS_152, new __VLS_152({
        ...{ 'onClick': {} },
        type: (__VLS_ctx.bindingAction === 'bind' ? 'primary' : 'danger'),
        loading: (__VLS_ctx.saving),
    }));
    const __VLS_154 = __VLS_153({
        ...{ 'onClick': {} },
        type: (__VLS_ctx.bindingAction === 'bind' ? 'primary' : 'danger'),
        loading: (__VLS_ctx.saving),
    }, ...__VLS_functionalComponentArgsRest(__VLS_153));
    let __VLS_156;
    let __VLS_157;
    let __VLS_158;
    const __VLS_159 = {
        onClick: (__VLS_ctx.applyBinding)
    };
    __VLS_155.slots.default;
    (__VLS_ctx.bindingAction === 'bind' ? '绑定' : '解绑');
    var __VLS_155;
}
var __VLS_135;
const __VLS_160 = {}.ElDialog;
/** @type {[typeof __VLS_components.ElDialog, typeof __VLS_components.elDialog, typeof __VLS_components.ElDialog, typeof __VLS_components.elDialog, ]} */ ;
// @ts-ignore
const __VLS_161 = __VLS_asFunctionalComponent(__VLS_160, new __VLS_160({
    modelValue: (__VLS_ctx.executeVisible),
    title: (`执行 Tool：${__VLS_ctx.selectedTool?.name || ''}`),
    width: "620px",
}));
const __VLS_162 = __VLS_161({
    modelValue: (__VLS_ctx.executeVisible),
    title: (`执行 Tool：${__VLS_ctx.selectedTool?.name || ''}`),
    width: "620px",
}, ...__VLS_functionalComponentArgsRest(__VLS_161));
__VLS_163.slots.default;
const __VLS_164 = {}.ElAlert;
/** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
// @ts-ignore
const __VLS_165 = __VLS_asFunctionalComponent(__VLS_164, new __VLS_164({
    title: "Tool Execute 会创建 Runtime Execution，并受 Agent/Tool 权限、启用状态和 Schema 校验约束。",
    type: "info",
    closable: (false),
}));
const __VLS_166 = __VLS_165({
    title: "Tool Execute 会创建 Runtime Execution，并受 Agent/Tool 权限、启用状态和 Schema 校验约束。",
    type: "info",
    closable: (false),
}, ...__VLS_functionalComponentArgsRest(__VLS_165));
const __VLS_168 = {}.ElForm;
/** @type {[typeof __VLS_components.ElForm, typeof __VLS_components.elForm, typeof __VLS_components.ElForm, typeof __VLS_components.elForm, ]} */ ;
// @ts-ignore
const __VLS_169 = __VLS_asFunctionalComponent(__VLS_168, new __VLS_168({
    labelWidth: "110px",
    ...{ class: "form" },
}));
const __VLS_170 = __VLS_169({
    labelWidth: "110px",
    ...{ class: "form" },
}, ...__VLS_functionalComponentArgsRest(__VLS_169));
__VLS_171.slots.default;
const __VLS_172 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_173 = __VLS_asFunctionalComponent(__VLS_172, new __VLS_172({
    label: "Agent",
}));
const __VLS_174 = __VLS_173({
    label: "Agent",
}, ...__VLS_functionalComponentArgsRest(__VLS_173));
__VLS_175.slots.default;
const __VLS_176 = {}.ElSelect;
/** @type {[typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, ]} */ ;
// @ts-ignore
const __VLS_177 = __VLS_asFunctionalComponent(__VLS_176, new __VLS_176({
    modelValue: (__VLS_ctx.selectedAgent),
    ...{ style: {} },
}));
const __VLS_178 = __VLS_177({
    modelValue: (__VLS_ctx.selectedAgent),
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_177));
__VLS_179.slots.default;
for (const [agent] of __VLS_getVForSourceType((__VLS_ctx.agents))) {
    const __VLS_180 = {}.ElOption;
    /** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
    // @ts-ignore
    const __VLS_181 = __VLS_asFunctionalComponent(__VLS_180, new __VLS_180({
        key: (agent.id),
        label: (agent.name),
        value: (agent.id),
    }));
    const __VLS_182 = __VLS_181({
        key: (agent.id),
        label: (agent.name),
        value: (agent.id),
    }, ...__VLS_functionalComponentArgsRest(__VLS_181));
}
var __VLS_179;
var __VLS_175;
const __VLS_184 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_185 = __VLS_asFunctionalComponent(__VLS_184, new __VLS_184({
    label: "Arguments",
}));
const __VLS_186 = __VLS_185({
    label: "Arguments",
}, ...__VLS_functionalComponentArgsRest(__VLS_185));
__VLS_187.slots.default;
const __VLS_188 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
const __VLS_189 = __VLS_asFunctionalComponent(__VLS_188, new __VLS_188({
    modelValue: (__VLS_ctx.argumentsText),
    type: "textarea",
    rows: (8),
}));
const __VLS_190 = __VLS_189({
    modelValue: (__VLS_ctx.argumentsText),
    type: "textarea",
    rows: (8),
}, ...__VLS_functionalComponentArgsRest(__VLS_189));
var __VLS_187;
var __VLS_171;
if (__VLS_ctx.executionResult) {
    const __VLS_192 = {}.ElAlert;
    /** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
    // @ts-ignore
    const __VLS_193 = __VLS_asFunctionalComponent(__VLS_192, new __VLS_192({
        title: (__VLS_ctx.executionResult),
        type: "success",
        showIcon: true,
    }));
    const __VLS_194 = __VLS_193({
        title: (__VLS_ctx.executionResult),
        type: "success",
        showIcon: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_193));
}
{
    const { footer: __VLS_thisSlot } = __VLS_163.slots;
    const __VLS_196 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_197 = __VLS_asFunctionalComponent(__VLS_196, new __VLS_196({
        ...{ 'onClick': {} },
    }));
    const __VLS_198 = __VLS_197({
        ...{ 'onClick': {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_197));
    let __VLS_200;
    let __VLS_201;
    let __VLS_202;
    const __VLS_203 = {
        onClick: (...[$event]) => {
            __VLS_ctx.executeVisible = false;
        }
    };
    __VLS_199.slots.default;
    var __VLS_199;
    const __VLS_204 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_205 = __VLS_asFunctionalComponent(__VLS_204, new __VLS_204({
        ...{ 'onClick': {} },
        type: "primary",
        loading: (__VLS_ctx.executing),
    }));
    const __VLS_206 = __VLS_205({
        ...{ 'onClick': {} },
        type: "primary",
        loading: (__VLS_ctx.executing),
    }, ...__VLS_functionalComponentArgsRest(__VLS_205));
    let __VLS_208;
    let __VLS_209;
    let __VLS_210;
    const __VLS_211 = {
        onClick: (__VLS_ctx.execute)
    };
    __VLS_207.slots.default;
    var __VLS_207;
}
var __VLS_163;
/** @type {__VLS_StyleScopedClasses['page']} */ ;
/** @type {__VLS_StyleScopedClasses['header']} */ ;
/** @type {__VLS_StyleScopedClasses['table']} */ ;
/** @type {__VLS_StyleScopedClasses['form']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            tools: tools,
            agents: agents,
            loading: loading,
            saving: saving,
            executing: executing,
            error: error,
            createVisible: createVisible,
            bindVisible: bindVisible,
            executeVisible: executeVisible,
            selectedTool: selectedTool,
            selectedAgent: selectedAgent,
            bindingAction: bindingAction,
            argumentsText: argumentsText,
            executionResult: executionResult,
            createForm: createForm,
            isAdmin: isAdmin,
            toggle: toggle,
            create: create,
            openBind: openBind,
            applyBinding: applyBinding,
            openExecute: openExecute,
            execute: execute,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
