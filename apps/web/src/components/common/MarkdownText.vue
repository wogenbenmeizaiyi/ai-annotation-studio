<template>
  <div class="markdown-text">
    <template v-for="(block, blockIndex) in blocks" :key="`${block.type}-${blockIndex}`">
      <h4 v-if="block.type === 'heading'" class="markdown-heading">
        <template v-for="(token, tokenIndex) in block.tokens" :key="tokenIndex">
          <strong v-if="token.type === 'strong'">{{ token.content }}</strong>
          <code v-else-if="token.type === 'code'">{{ token.content }}</code>
          <span v-else>{{ token.content }}</span>
        </template>
      </h4>
      <div v-else-if="block.type === 'ordered'" class="markdown-list-item">
        <span class="markdown-list-marker">{{ block.marker }}.</span>
        <p>
          <template v-for="(token, tokenIndex) in block.tokens" :key="tokenIndex">
            <strong v-if="token.type === 'strong'">{{ token.content }}</strong>
            <code v-else-if="token.type === 'code'">{{ token.content }}</code>
            <span v-else>{{ token.content }}</span>
          </template>
        </p>
      </div>
      <div v-else-if="block.type === 'unordered'" class="markdown-list-item">
        <span class="markdown-list-marker">•</span>
        <p>
          <template v-for="(token, tokenIndex) in block.tokens" :key="tokenIndex">
            <strong v-if="token.type === 'strong'">{{ token.content }}</strong>
            <code v-else-if="token.type === 'code'">{{ token.content }}</code>
            <span v-else>{{ token.content }}</span>
          </template>
        </p>
      </div>
      <p v-else class="markdown-paragraph">
        <template v-for="(token, tokenIndex) in block.tokens" :key="tokenIndex">
          <strong v-if="token.type === 'strong'">{{ token.content }}</strong>
          <code v-else-if="token.type === 'code'">{{ token.content }}</code>
          <span v-else>{{ token.content }}</span>
        </template>
      </p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type InlineToken = {
  type: 'text' | 'strong' | 'code'
  content: string
}

type MarkdownBlock = {
  type: 'heading' | 'paragraph' | 'ordered' | 'unordered'
  marker?: string
  tokens: InlineToken[]
}

const props = defineProps<{
  content: string
}>()

const parseInline = (text: string): InlineToken[] => {
  const tokens: InlineToken[] = []
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`)/g
  let cursor = 0

  for (const match of text.matchAll(pattern)) {
    const index = match.index ?? 0
    if (index > cursor) tokens.push({ type: 'text', content: text.slice(cursor, index) })

    const value = match[0]
    tokens.push({
      type: value.startsWith('**') ? 'strong' : 'code',
      content: value.startsWith('**') ? value.slice(2, -2) : value.slice(1, -1),
    })
    cursor = index + value.length
  }

  if (cursor < text.length) tokens.push({ type: 'text', content: text.slice(cursor) })
  return tokens.length ? tokens : [{ type: 'text', content: text }]
}

const blocks = computed<MarkdownBlock[]>(() => {
  const normalized = props.content
    .replace(/\r\n?/g, '\n')
    .replace(/\s+(?=\d+\.\s+(?:\*\*|[^\s]))/g, '\n')

  return normalized
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const heading = line.match(/^#{1,6}\s+(.+)$/)
      if (heading) return { type: 'heading', tokens: parseInline(heading[1] ?? '') }

      const ordered = line.match(/^(\d+)\.\s+(.+)$/)
      if (ordered) {
        return {
          type: 'ordered',
          marker: ordered[1],
          tokens: parseInline(ordered[2] ?? ''),
        }
      }

      const unordered = line.match(/^[-*]\s+(.+)$/)
      if (unordered) return { type: 'unordered', tokens: parseInline(unordered[1] ?? '') }

      return { type: 'paragraph', tokens: parseInline(line) }
    })
})
</script>

<style scoped>
.markdown-text {
  display: grid;
  gap: 10px;
  line-height: 1.7;
  color: var(--text-muted);
  font-size: 13px;
}

.markdown-heading,
.markdown-paragraph,
.markdown-list-item p {
  margin: 0;
}

.markdown-heading {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.markdown-list-item {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 4px;
}

.markdown-list-marker {
  color: var(--accent);
  font-weight: 700;
  font-family: var(--font-italic);
  text-align: right;
}

strong {
  font-weight: 600;
  color: var(--ink);
}

code {
  padding: 1px 5px;
  background: var(--bg-sunken);
  color: var(--accent);
  border: 1px solid var(--border);
  font-family: var(--font-mono);
  font-size: 0.9em;
}
</style>
