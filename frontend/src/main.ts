import { createApp } from "vue";
import { createPinia } from "pinia";
import {
  ElAlert, ElButton, ElCard, ElCol, ElDescriptions, ElDescriptionsItem, ElDialog, ElDivider, ElDrawer, ElEmpty,
  ElForm, ElFormItem, ElIcon, ElInput, ElInputNumber, ElOption, ElPagination, ElRow, ElScrollbar, ElSelect,
  ElSlider, ElSwitch, ElTable, ElTableColumn, ElTabPane, ElTabs, ElTag, ElTimeline, ElTimelineItem, vLoading,
} from "element-plus";
import "element-plus/dist/index.css";
import App from "./App.vue";
import router from "./router";
import "./styles/global.css";

const app = createApp(App);
const components = {
  ElAlert, ElButton, ElCard, ElCol, ElDescriptions, ElDescriptionsItem, ElDialog, ElDivider, ElDrawer, ElEmpty,
  ElForm, ElFormItem, ElIcon, ElInput, ElInputNumber, ElOption, ElPagination, ElRow, ElScrollbar, ElSelect,
  ElSlider, ElSwitch, ElTable, ElTableColumn, ElTabPane, ElTabs, ElTag, ElTimeline, ElTimelineItem,
};
for (const [name, component] of Object.entries(components)) app.component(name, component);
app.directive("loading", vLoading);
app.use(createPinia()).use(router).mount("#app");
