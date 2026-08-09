<script setup lang="ts">
import { AlertTriangle, CheckCircle2, History, LoaderCircle } from "lucide-vue-next";
import { computed } from "vue";

import type {
  ChatMemoryState,
  ChatMessage,
  MemoryStageSseEvent
} from "@agent-py/api-contracts";

const emit = defineEmits<{ retry: [messageId: string] }>();
const props = defineProps<{
  readonly disabled: boolean;
  readonly memory: ChatMemoryState | null;
  readonly messages: readonly ChatMessage[];
  readonly stage: MemoryStageSseEvent["memory"] | null;
}>();

const failedMessage = computed(() =>
  [...props.messages]
    .reverse()
    .find(
      (message) =>
        message.role === "user" && message.metadata.memoryPreparationStatus === "failed"
    )
);
const statusText = computed(() => {
  if (props.stage?.status === "running") return "正在准备上下文";
  if (props.stage?.status === "succeeded") return "上下文准备完成";
  if (props.stage?.status === "failed") return "上下文准备失败";
  if (props.memory?.status === "failed") return "最近一次压缩失败";
  if (props.memory?.status === "succeeded") return "快照已校验";
  return "尚未生成快照";
});
</script>

<template>
  <section class="memory-inspector" aria-label="Chat 记忆检查器">
    <div class="memory-inspector__summary">
      <span class="memory-inspector__label"><History :size="14" />记忆 v{{ memory?.version ?? 0 }}</span>
      <span :class="['memory-inspector__status', `is-${stage?.status ?? memory?.status ?? 'idle'}`]">
        <LoaderCircle v-if="stage?.status === 'running'" :size="13" class="memory-inspector__spin" />
        <AlertTriangle v-else-if="memory?.status === 'failed'" :size="13" />
        <CheckCircle2 v-else :size="13" />
        {{ statusText }}
      </span>
      <span>压缩边界 {{ memory?.compactedMessageCount ?? 0 }} 条</span>
      <span>有效约束 {{ memory?.snapshot.activeConstraints.length ?? 0 }} 条</span>
      <span>已废止 {{ memory?.snapshot.supersededFacts.length ?? 0 }} 条</span>
      <button
        v-if="failedMessage"
        type="button"
        :disabled="disabled"
        @click="emit('retry', failedMessage.id)"
      >重试该消息</button>
    </div>
    <details v-if="memory && (memory.snapshot.activeConstraints.length || memory.snapshot.supersededFacts.length)">
      <summary>查看结构化记忆与来源</summary>
      <div class="memory-inspector__grid">
        <article>
          <h3>当前有效约束</h3>
          <p v-if="memory.snapshot.activeConstraints.length === 0">无</p>
          <ul v-else>
            <li v-for="item in memory.snapshot.activeConstraints" :key="`${item.key}-${item.sourceMessageId}`">
              <strong>{{ item.key }}</strong><span>{{ item.value }}</span><code>{{ item.sourceMessageId }}</code>
            </li>
          </ul>
        </article>
        <article>
          <h3>已废止事实</h3>
          <p v-if="memory.snapshot.supersededFacts.length === 0">无</p>
          <ul v-else>
            <li v-for="item in memory.snapshot.supersededFacts" :key="`${item.key}-${item.sourceMessageId}`">
              <strong>{{ item.key }}</strong><span>{{ item.value }}</span>
              <code>{{ item.sourceMessageId }} → {{ item.supersededByMessageId }}</code>
            </li>
          </ul>
        </article>
      </div>
    </details>
  </section>
</template>

<style scoped>
.memory-inspector { border-bottom: 1px solid var(--line); padding: 0.55rem clamp(1rem, 3vw, 2rem); }
.memory-inspector__summary { align-items: center; color: var(--text-tertiary); display: flex; flex-wrap: wrap; font-size: 0.7rem; gap: 0.5rem 1rem; }
.memory-inspector__label, .memory-inspector__status { align-items: center; display: inline-flex; gap: 0.3rem; }
.memory-inspector__label { color: var(--text-primary); font-weight: 700; }
.memory-inspector__status.is-failed { color: var(--status-error-text); }
.memory-inspector__status.is-running { color: var(--status-running-text); }
button { background: var(--surface-subtle); border: 1px solid var(--line-strong); border-radius: 0.35rem; font-size: 0.7rem; padding: 0.28rem 0.55rem; }
details { margin-top: 0.5rem; }
summary { color: var(--text-secondary); cursor: pointer; font-size: 0.72rem; }
.memory-inspector__grid { display: grid; gap: 0.75rem; grid-template-columns: repeat(2, minmax(0, 1fr)); padding-top: 0.65rem; }
article { background: var(--surface-subtle); border: 1px solid var(--line); border-radius: 0.5rem; padding: 0.65rem; }
h3, p, ul { margin: 0; }
h3 { font-size: 0.72rem; margin-bottom: 0.45rem; }
ul { display: grid; gap: 0.4rem; list-style: none; padding: 0; }
li { display: grid; font-size: 0.68rem; gap: 0.15rem; }
code { color: var(--text-tertiary); font-size: 0.62rem; overflow-wrap: anywhere; }
.memory-inspector__spin { animation: memory-spin 0.8s linear infinite; }
@keyframes memory-spin { to { transform: rotate(360deg); } }
</style>
