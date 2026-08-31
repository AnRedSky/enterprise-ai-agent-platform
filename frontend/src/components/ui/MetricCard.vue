<script setup lang="ts">
import { computed } from "vue";
import { TrendCharts } from "@element-plus/icons-vue";

const props = withDefaults(defineProps<{
  label: string;
  value: string | number;
  description?: string;
  trend?: string;
  trendDirection?: "up" | "down" | "neutral";
}>(), { description: undefined, trend: undefined, trendDirection: "neutral" });
const trendClass = computed(() => `is-${props.trendDirection}`);
</script>

<template>
  <article class="ui-metric-card">
    <div class="ui-metric-card__label">{{ label }}</div>
    <div class="ui-metric-card__value">{{ value }}</div>
    <div v-if="trend || description" class="ui-metric-card__meta">
      <span v-if="trend" class="ui-metric-card__trend" :class="trendClass"><el-icon><TrendCharts /></el-icon>{{ trend }}</span>
      <span v-if="description">{{ description }}</span>
    </div>
  </article>
</template>

<style scoped>
.ui-metric-card { min-width:0; padding:20px; border:1px solid var(--ui-border-default); border-radius:var(--ui-radius-lg); background:var(--ui-bg-surface); box-shadow:var(--ui-shadow-xs); }
.ui-metric-card__label { color:var(--ui-text-secondary); font-size:12px; line-height:18px; font-weight:600; }
.ui-metric-card__value { margin-top:8px; color:var(--ui-text-primary); font-size:28px; line-height:34px; font-weight:650; letter-spacing:-.025em; font-variant-numeric:tabular-nums; }
.ui-metric-card__meta { display:flex; align-items:center; gap:8px; min-height:18px; margin-top:8px; color:var(--ui-text-tertiary); font-size:11px; line-height:18px; }
.ui-metric-card__trend { display:inline-flex; align-items:center; gap:3px; font-weight:600; }
.ui-metric-card__trend.is-up { color:var(--ui-color-success-600); }
.ui-metric-card__trend.is-down { color:var(--ui-color-danger-600); }
.ui-metric-card__trend.is-neutral { color:var(--ui-text-tertiary); }
</style>
