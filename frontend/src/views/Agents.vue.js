import { onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { archiveAgent, createAgent, createVersion as createAgentVersion, listAgents, listVersions, publishAgent } from "../api/agents";
import { streamChat } from "../api/chat";
const agents = ref([]), versions = ref([]);
const loadingAgents = ref(false), saving = ref(false), savingVersion = ref(false), chatLoading = ref(false);
const publishingVersionId = ref("");
const dialogVisible = ref(false), versionsVisible = ref(false), chatVisible = ref(false);
const error = ref(""), selected = ref(null), input = ref(""), executionId = ref("");
const sessionId = ref(), messages = ref([]);
const form = ref({ name: "企业智能助手", description: "", system_prompt: "你是一个企业级 AI 助手，请准确、简洁地回答用户问题。", model_id: "mock-model" });
const versionForm = ref({ system_prompt: "", model_id: "mock-model" });
async function load() { loadingAgents.value = true; error.value = ""; try {
    agents.value = await listAgents();
}
catch (e) {
    error.value = e instanceof Error ? e.message : "Agent 列表加载失败";
}
finally {
    loadingAgents.value = false;
} }
async function create() { saving.value = true; try {
    await createAgent(form.value);
    dialogVisible.value = false;
    await load();
    ElMessage.success("Agent 创建成功，请发布后再进行 Chat 调试");
}
catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "Agent 创建失败");
}
finally {
    saving.value = false;
} }
async function openVersions(agent) { selected.value = agent; versionsVisible.value = true; versionForm.value = { system_prompt: "", model_id: agent.model_id || "mock-model" }; try {
    versions.value = await listVersions(agent.id);
}
catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "版本加载失败");
} }
async function createVersion() { if (!selected.value || !versionForm.value.system_prompt.trim() || selected.value.status === "archived")
    return; savingVersion.value = true; try {
    await createAgentVersion(selected.value.id, versionForm.value);
    versions.value = await listVersions(selected.value.id);
    await load();
    selected.value = agents.value.find(a => a.id === selected.value?.id) || selected.value;
    ElMessage.success("版本创建成功，请发布目标版本后生效");
}
catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "版本创建失败");
}
finally {
    savingVersion.value = false;
} }
async function publishVersion(version) { if (!selected.value || selected.value.status === "archived")
    return; publishingVersionId.value = version.id; try {
    await publishAgent(selected.value.id, version.id);
    versions.value = await listVersions(selected.value.id);
    await load();
    selected.value = agents.value.find(a => a.id === selected.value?.id) || selected.value;
    ElMessage.success(`已发布 ${version.version}`);
}
catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "Agent 发布失败");
}
finally {
    publishingVersionId.value = "";
} }
async function publishLatest(agent) { try {
    const items = await listVersions(agent.id);
    if (!items.length)
        throw new Error("没有可发布版本");
    await publishAgent(agent.id, items[0].id);
    await load();
    ElMessage.success(`已发布 ${items[0].version}`);
}
catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "Agent 发布失败");
} }
async function archive(agent) { try {
    await ElMessageBox.confirm(`确定归档 Agent「${agent.name}」吗？归档后不能创建新版本或继续 Chat。`, "归档确认", { type: "warning" });
    await archiveAgent(agent.id);
    await load();
    ElMessage.success("Agent 已归档");
}
catch (e) {
    if (e !== "cancel" && e !== "close")
        ElMessage.error(e instanceof Error ? e.message : "Agent 归档失败");
} }
function openChat(agent) { selected.value = agent; input.value = ""; sessionId.value = undefined; executionId.value = ""; messages.value = []; chatVisible.value = true; }
async function execute() { if (!selected.value || !input.value.trim() || chatLoading.value)
    return; const text = input.value.trim(); input.value = ""; messages.value.push({ role: "user", content: text }, { role: "assistant", content: "" }); chatLoading.value = true; try {
    await streamChat({ agent_id: selected.value.id, input: text, session_id: sessionId.value, memory_limit: 20 }, event => { if (event.type === "start")
        sessionId.value = event.session_id; if (event.type === "delta")
        messages.value[messages.value.length - 1].content += event.content; if (event.type === "done")
        executionId.value = event.execution_id; });
}
catch (e) {
    messages.value[messages.value.length - 1].content = e instanceof Error ? e.message : "Chat 执行失败";
    ElMessage.error("Chat 执行失败");
}
finally {
    chatLoading.value = false;
} }
onMounted(load);
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['header']} */ ;
/** @type {__VLS_StyleScopedClasses['message']} */ ;
/** @type {__VLS_StyleScopedClasses['message']} */ ;
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
        __VLS_ctx.dialogVisible = true;
    }
};
__VLS_3.slots.default;
var __VLS_3;
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
    data: (__VLS_ctx.agents),
    border: true,
    ...{ class: "table" },
}));
const __VLS_18 = __VLS_17({
    data: (__VLS_ctx.agents),
    border: true,
    ...{ class: "table" },
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
__VLS_asFunctionalDirective(__VLS_directives.vLoading)(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.loadingAgents) }, null, null);
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
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
    label: "当前生效版本",
    width: "180",
}));
const __VLS_26 = __VLS_25({
    label: "当前生效版本",
    width: "180",
}, ...__VLS_functionalComponentArgsRest(__VLS_25));
__VLS_27.slots.default;
{
    const { default: __VLS_thisSlot } = __VLS_27.slots;
    const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
    (row.version || "未发布");
    if (row.version) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "published-badge" },
        });
    }
}
var __VLS_27;
const __VLS_28 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
    prop: "model_id",
    label: "模型",
    width: "160",
}));
const __VLS_30 = __VLS_29({
    prop: "model_id",
    label: "模型",
    width: "160",
}, ...__VLS_functionalComponentArgsRest(__VLS_29));
const __VLS_32 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
    prop: "status",
    label: "状态",
    width: "110",
}));
const __VLS_34 = __VLS_33({
    prop: "status",
    label: "状态",
    width: "110",
}, ...__VLS_functionalComponentArgsRest(__VLS_33));
const __VLS_36 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
    label: "操作",
    minWidth: "430",
}));
const __VLS_38 = __VLS_37({
    label: "操作",
    minWidth: "430",
}, ...__VLS_functionalComponentArgsRest(__VLS_37));
__VLS_39.slots.default;
{
    const { default: __VLS_thisSlot } = __VLS_39.slots;
    const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
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
            __VLS_ctx.openVersions(row);
        }
    };
    __VLS_43.slots.default;
    var __VLS_43;
    const __VLS_48 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_49 = __VLS_asFunctionalComponent(__VLS_48, new __VLS_48({
        ...{ 'onClick': {} },
        link: true,
        type: "primary",
        disabled: (row.status !== 'published'),
    }));
    const __VLS_50 = __VLS_49({
        ...{ 'onClick': {} },
        link: true,
        type: "primary",
        disabled: (row.status !== 'published'),
    }, ...__VLS_functionalComponentArgsRest(__VLS_49));
    let __VLS_52;
    let __VLS_53;
    let __VLS_54;
    const __VLS_55 = {
        onClick: (...[$event]) => {
            __VLS_ctx.openChat(row);
        }
    };
    __VLS_51.slots.default;
    var __VLS_51;
    if (row.status !== 'published' && row.status !== 'archived') {
        const __VLS_56 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        const __VLS_57 = __VLS_asFunctionalComponent(__VLS_56, new __VLS_56({
            ...{ 'onClick': {} },
            link: true,
            type: "success",
        }));
        const __VLS_58 = __VLS_57({
            ...{ 'onClick': {} },
            link: true,
            type: "success",
        }, ...__VLS_functionalComponentArgsRest(__VLS_57));
        let __VLS_60;
        let __VLS_61;
        let __VLS_62;
        const __VLS_63 = {
            onClick: (...[$event]) => {
                if (!(row.status !== 'published' && row.status !== 'archived'))
                    return;
                __VLS_ctx.publishLatest(row);
            }
        };
        __VLS_59.slots.default;
        var __VLS_59;
    }
    if (row.status === 'published') {
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
                if (!(row.status === 'published'))
                    return;
                __VLS_ctx.archive(row);
            }
        };
        __VLS_67.slots.default;
        var __VLS_67;
    }
}
var __VLS_39;
var __VLS_19;
if (!__VLS_ctx.loadingAgents && !__VLS_ctx.agents.length) {
    const __VLS_72 = {}.ElEmpty;
    /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
    // @ts-ignore
    const __VLS_73 = __VLS_asFunctionalComponent(__VLS_72, new __VLS_72({
        description: "暂无 Agent，请先创建一个。",
    }));
    const __VLS_74 = __VLS_73({
        description: "暂无 Agent，请先创建一个。",
    }, ...__VLS_functionalComponentArgsRest(__VLS_73));
}
const __VLS_76 = {}.ElDialog;
/** @type {[typeof __VLS_components.ElDialog, typeof __VLS_components.elDialog, typeof __VLS_components.ElDialog, typeof __VLS_components.elDialog, ]} */ ;
// @ts-ignore
const __VLS_77 = __VLS_asFunctionalComponent(__VLS_76, new __VLS_76({
    modelValue: (__VLS_ctx.dialogVisible),
    title: "创建 Agent",
    width: "560px",
}));
const __VLS_78 = __VLS_77({
    modelValue: (__VLS_ctx.dialogVisible),
    title: "创建 Agent",
    width: "560px",
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
    modelValue: (__VLS_ctx.form.name),
}));
const __VLS_90 = __VLS_89({
    modelValue: (__VLS_ctx.form.name),
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
    modelValue: (__VLS_ctx.form.description),
}));
const __VLS_98 = __VLS_97({
    modelValue: (__VLS_ctx.form.description),
}, ...__VLS_functionalComponentArgsRest(__VLS_97));
var __VLS_95;
const __VLS_100 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_101 = __VLS_asFunctionalComponent(__VLS_100, new __VLS_100({
    label: "System Prompt",
    required: true,
}));
const __VLS_102 = __VLS_101({
    label: "System Prompt",
    required: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_101));
__VLS_103.slots.default;
const __VLS_104 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
const __VLS_105 = __VLS_asFunctionalComponent(__VLS_104, new __VLS_104({
    modelValue: (__VLS_ctx.form.system_prompt),
    type: "textarea",
    rows: (5),
}));
const __VLS_106 = __VLS_105({
    modelValue: (__VLS_ctx.form.system_prompt),
    type: "textarea",
    rows: (5),
}, ...__VLS_functionalComponentArgsRest(__VLS_105));
var __VLS_103;
const __VLS_108 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_109 = __VLS_asFunctionalComponent(__VLS_108, new __VLS_108({
    label: "模型",
    required: true,
}));
const __VLS_110 = __VLS_109({
    label: "模型",
    required: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_109));
__VLS_111.slots.default;
const __VLS_112 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
const __VLS_113 = __VLS_asFunctionalComponent(__VLS_112, new __VLS_112({
    modelValue: (__VLS_ctx.form.model_id),
}));
const __VLS_114 = __VLS_113({
    modelValue: (__VLS_ctx.form.model_id),
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
            __VLS_ctx.dialogVisible = false;
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
    modelValue: (__VLS_ctx.versionsVisible),
    title: (`Agent Versions · ${__VLS_ctx.selected?.name || ''}`),
    width: "760px",
}));
const __VLS_134 = __VLS_133({
    modelValue: (__VLS_ctx.versionsVisible),
    title: (`Agent Versions · ${__VLS_ctx.selected?.name || ''}`),
    width: "760px",
}, ...__VLS_functionalComponentArgsRest(__VLS_133));
__VLS_135.slots.default;
if (__VLS_ctx.selected?.status === 'archived') {
    const __VLS_136 = {}.ElAlert;
    /** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
    // @ts-ignore
    const __VLS_137 = __VLS_asFunctionalComponent(__VLS_136, new __VLS_136({
        title: "Agent 已归档，不能创建或发布新版本。",
        type: "warning",
        showIcon: true,
    }));
    const __VLS_138 = __VLS_137({
        title: "Agent 已归档，不能创建或发布新版本。",
        type: "warning",
        showIcon: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_137));
}
const __VLS_140 = {}.ElTable;
/** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
// @ts-ignore
const __VLS_141 = __VLS_asFunctionalComponent(__VLS_140, new __VLS_140({
    data: (__VLS_ctx.versions),
    border: true,
}));
const __VLS_142 = __VLS_141({
    data: (__VLS_ctx.versions),
    border: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_141));
__VLS_143.slots.default;
const __VLS_144 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_145 = __VLS_asFunctionalComponent(__VLS_144, new __VLS_144({
    prop: "version",
    label: "版本",
    width: "130",
}));
const __VLS_146 = __VLS_145({
    prop: "version",
    label: "版本",
    width: "130",
}, ...__VLS_functionalComponentArgsRest(__VLS_145));
__VLS_147.slots.default;
{
    const { default: __VLS_thisSlot } = __VLS_147.slots;
    const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
    (row.version);
    if (row.is_published) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "published-badge" },
        });
    }
}
var __VLS_147;
const __VLS_148 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_149 = __VLS_asFunctionalComponent(__VLS_148, new __VLS_148({
    prop: "model_id",
    label: "模型",
    width: "160",
}));
const __VLS_150 = __VLS_149({
    prop: "model_id",
    label: "模型",
    width: "160",
}, ...__VLS_functionalComponentArgsRest(__VLS_149));
const __VLS_152 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_153 = __VLS_asFunctionalComponent(__VLS_152, new __VLS_152({
    prop: "created_at",
    label: "创建时间",
}));
const __VLS_154 = __VLS_153({
    prop: "created_at",
    label: "创建时间",
}, ...__VLS_functionalComponentArgsRest(__VLS_153));
const __VLS_156 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_157 = __VLS_asFunctionalComponent(__VLS_156, new __VLS_156({
    label: "操作",
    width: "110",
}));
const __VLS_158 = __VLS_157({
    label: "操作",
    width: "110",
}, ...__VLS_functionalComponentArgsRest(__VLS_157));
__VLS_159.slots.default;
{
    const { default: __VLS_thisSlot } = __VLS_159.slots;
    const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
    if (!row.is_published && __VLS_ctx.selected?.status !== 'archived') {
        const __VLS_160 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        const __VLS_161 = __VLS_asFunctionalComponent(__VLS_160, new __VLS_160({
            ...{ 'onClick': {} },
            link: true,
            type: "success",
            loading: (__VLS_ctx.publishingVersionId === row.id),
        }));
        const __VLS_162 = __VLS_161({
            ...{ 'onClick': {} },
            link: true,
            type: "success",
            loading: (__VLS_ctx.publishingVersionId === row.id),
        }, ...__VLS_functionalComponentArgsRest(__VLS_161));
        let __VLS_164;
        let __VLS_165;
        let __VLS_166;
        const __VLS_167 = {
            onClick: (...[$event]) => {
                if (!(!row.is_published && __VLS_ctx.selected?.status !== 'archived'))
                    return;
                __VLS_ctx.publishVersion(row);
            }
        };
        __VLS_163.slots.default;
        var __VLS_163;
    }
}
var __VLS_159;
var __VLS_143;
const __VLS_168 = {}.ElDivider;
/** @type {[typeof __VLS_components.ElDivider, typeof __VLS_components.elDivider, ]} */ ;
// @ts-ignore
const __VLS_169 = __VLS_asFunctionalComponent(__VLS_168, new __VLS_168({}));
const __VLS_170 = __VLS_169({}, ...__VLS_functionalComponentArgsRest(__VLS_169));
const __VLS_172 = {}.ElForm;
/** @type {[typeof __VLS_components.ElForm, typeof __VLS_components.elForm, typeof __VLS_components.ElForm, typeof __VLS_components.elForm, ]} */ ;
// @ts-ignore
const __VLS_173 = __VLS_asFunctionalComponent(__VLS_172, new __VLS_172({
    labelWidth: "100px",
}));
const __VLS_174 = __VLS_173({
    labelWidth: "100px",
}, ...__VLS_functionalComponentArgsRest(__VLS_173));
__VLS_175.slots.default;
const __VLS_176 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_177 = __VLS_asFunctionalComponent(__VLS_176, new __VLS_176({
    label: "System Prompt",
}));
const __VLS_178 = __VLS_177({
    label: "System Prompt",
}, ...__VLS_functionalComponentArgsRest(__VLS_177));
__VLS_179.slots.default;
const __VLS_180 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
const __VLS_181 = __VLS_asFunctionalComponent(__VLS_180, new __VLS_180({
    modelValue: (__VLS_ctx.versionForm.system_prompt),
    type: "textarea",
    rows: (3),
    disabled: (__VLS_ctx.selected?.status === 'archived'),
}));
const __VLS_182 = __VLS_181({
    modelValue: (__VLS_ctx.versionForm.system_prompt),
    type: "textarea",
    rows: (3),
    disabled: (__VLS_ctx.selected?.status === 'archived'),
}, ...__VLS_functionalComponentArgsRest(__VLS_181));
var __VLS_179;
const __VLS_184 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_185 = __VLS_asFunctionalComponent(__VLS_184, new __VLS_184({
    label: "模型",
}));
const __VLS_186 = __VLS_185({
    label: "模型",
}, ...__VLS_functionalComponentArgsRest(__VLS_185));
__VLS_187.slots.default;
const __VLS_188 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
const __VLS_189 = __VLS_asFunctionalComponent(__VLS_188, new __VLS_188({
    modelValue: (__VLS_ctx.versionForm.model_id),
    disabled: (__VLS_ctx.selected?.status === 'archived'),
}));
const __VLS_190 = __VLS_189({
    modelValue: (__VLS_ctx.versionForm.model_id),
    disabled: (__VLS_ctx.selected?.status === 'archived'),
}, ...__VLS_functionalComponentArgsRest(__VLS_189));
var __VLS_187;
var __VLS_175;
{
    const { footer: __VLS_thisSlot } = __VLS_135.slots;
    const __VLS_192 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_193 = __VLS_asFunctionalComponent(__VLS_192, new __VLS_192({
        ...{ 'onClick': {} },
    }));
    const __VLS_194 = __VLS_193({
        ...{ 'onClick': {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_193));
    let __VLS_196;
    let __VLS_197;
    let __VLS_198;
    const __VLS_199 = {
        onClick: (...[$event]) => {
            __VLS_ctx.versionsVisible = false;
        }
    };
    __VLS_195.slots.default;
    var __VLS_195;
    const __VLS_200 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_201 = __VLS_asFunctionalComponent(__VLS_200, new __VLS_200({
        ...{ 'onClick': {} },
        type: "primary",
        loading: (__VLS_ctx.savingVersion),
        disabled: (__VLS_ctx.selected?.status === 'archived'),
    }));
    const __VLS_202 = __VLS_201({
        ...{ 'onClick': {} },
        type: "primary",
        loading: (__VLS_ctx.savingVersion),
        disabled: (__VLS_ctx.selected?.status === 'archived'),
    }, ...__VLS_functionalComponentArgsRest(__VLS_201));
    let __VLS_204;
    let __VLS_205;
    let __VLS_206;
    const __VLS_207 = {
        onClick: (__VLS_ctx.createVersion)
    };
    __VLS_203.slots.default;
    var __VLS_203;
}
var __VLS_135;
const __VLS_208 = {}.ElDialog;
/** @type {[typeof __VLS_components.ElDialog, typeof __VLS_components.elDialog, typeof __VLS_components.ElDialog, typeof __VLS_components.elDialog, ]} */ ;
// @ts-ignore
const __VLS_209 = __VLS_asFunctionalComponent(__VLS_208, new __VLS_208({
    modelValue: (__VLS_ctx.chatVisible),
    title: (`调试：${__VLS_ctx.selected?.name || ''}`),
    width: "720px",
}));
const __VLS_210 = __VLS_209({
    modelValue: (__VLS_ctx.chatVisible),
    title: (`调试：${__VLS_ctx.selected?.name || ''}`),
    width: "720px",
}, ...__VLS_functionalComponentArgsRest(__VLS_209));
__VLS_211.slots.default;
const __VLS_212 = {}.ElScrollbar;
/** @type {[typeof __VLS_components.ElScrollbar, typeof __VLS_components.elScrollbar, typeof __VLS_components.ElScrollbar, typeof __VLS_components.elScrollbar, ]} */ ;
// @ts-ignore
const __VLS_213 = __VLS_asFunctionalComponent(__VLS_212, new __VLS_212({
    height: "360px",
    ...{ class: "messages" },
}));
const __VLS_214 = __VLS_213({
    height: "360px",
    ...{ class: "messages" },
}, ...__VLS_functionalComponentArgsRest(__VLS_213));
__VLS_215.slots.default;
for (const [message, index] of __VLS_getVForSourceType((__VLS_ctx.messages))) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        key: (index),
        ...{ class: (['message', message.role]) },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.b, __VLS_intrinsicElements.b)({});
    (message.role === 'user' ? '你' : 'Agent');
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    (message.content);
}
if (!__VLS_ctx.messages.length) {
    const __VLS_216 = {}.ElEmpty;
    /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
    // @ts-ignore
    const __VLS_217 = __VLS_asFunctionalComponent(__VLS_216, new __VLS_216({
        description: "输入消息开始调试",
    }));
    const __VLS_218 = __VLS_217({
        description: "输入消息开始调试",
    }, ...__VLS_functionalComponentArgsRest(__VLS_217));
}
var __VLS_215;
const __VLS_220 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
const __VLS_221 = __VLS_asFunctionalComponent(__VLS_220, new __VLS_220({
    ...{ 'onKeyup': {} },
    modelValue: (__VLS_ctx.input),
    type: "textarea",
    rows: (4),
    placeholder: "输入消息...",
}));
const __VLS_222 = __VLS_221({
    ...{ 'onKeyup': {} },
    modelValue: (__VLS_ctx.input),
    type: "textarea",
    rows: (4),
    placeholder: "输入消息...",
}, ...__VLS_functionalComponentArgsRest(__VLS_221));
let __VLS_224;
let __VLS_225;
let __VLS_226;
const __VLS_227 = {
    onKeyup: (__VLS_ctx.execute)
};
var __VLS_223;
if (__VLS_ctx.executionId) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "meta" },
    });
    (__VLS_ctx.executionId);
}
{
    const { footer: __VLS_thisSlot } = __VLS_211.slots;
    const __VLS_228 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_229 = __VLS_asFunctionalComponent(__VLS_228, new __VLS_228({
        ...{ 'onClick': {} },
    }));
    const __VLS_230 = __VLS_229({
        ...{ 'onClick': {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_229));
    let __VLS_232;
    let __VLS_233;
    let __VLS_234;
    const __VLS_235 = {
        onClick: (...[$event]) => {
            __VLS_ctx.chatVisible = false;
        }
    };
    __VLS_231.slots.default;
    var __VLS_231;
    const __VLS_236 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_237 = __VLS_asFunctionalComponent(__VLS_236, new __VLS_236({
        ...{ 'onClick': {} },
        type: "primary",
        loading: (__VLS_ctx.chatLoading),
        disabled: (!__VLS_ctx.input.trim()),
    }));
    const __VLS_238 = __VLS_237({
        ...{ 'onClick': {} },
        type: "primary",
        loading: (__VLS_ctx.chatLoading),
        disabled: (!__VLS_ctx.input.trim()),
    }, ...__VLS_functionalComponentArgsRest(__VLS_237));
    let __VLS_240;
    let __VLS_241;
    let __VLS_242;
    const __VLS_243 = {
        onClick: (__VLS_ctx.execute)
    };
    __VLS_239.slots.default;
    var __VLS_239;
}
var __VLS_211;
/** @type {__VLS_StyleScopedClasses['page']} */ ;
/** @type {__VLS_StyleScopedClasses['header']} */ ;
/** @type {__VLS_StyleScopedClasses['table']} */ ;
/** @type {__VLS_StyleScopedClasses['published-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['published-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['messages']} */ ;
/** @type {__VLS_StyleScopedClasses['meta']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            agents: agents,
            versions: versions,
            loadingAgents: loadingAgents,
            saving: saving,
            savingVersion: savingVersion,
            chatLoading: chatLoading,
            publishingVersionId: publishingVersionId,
            dialogVisible: dialogVisible,
            versionsVisible: versionsVisible,
            chatVisible: chatVisible,
            error: error,
            selected: selected,
            input: input,
            executionId: executionId,
            messages: messages,
            form: form,
            versionForm: versionForm,
            create: create,
            openVersions: openVersions,
            createVersion: createVersion,
            publishVersion: publishVersion,
            publishLatest: publishLatest,
            archive: archive,
            openChat: openChat,
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
