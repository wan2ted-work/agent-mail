<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
    <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
      <!-- Header -->
      <div class="p-6 border-b border-gray-200 flex items-start justify-between">
        <div class="flex-1 min-w-0">
          <h2 class="text-2xl font-bold text-gray-900 mb-2">
            {{ decodeHeader(email.subject) || '(No Subject)' }}
          </h2>
          <div class="space-y-1 text-sm">
            <div class="flex items-center gap-2">
              <span class="text-gray-500">From:</span>
              <span class="font-medium text-gray-900">
                {{ decodeHeader(email.from_name) || email.from_email }}
              </span>
              <span
                v-if="email.from_name"
                class="text-gray-500"
              >
                &lt;{{ email.from_email }}&gt;
              </span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-gray-500">To:</span>
              <span class="text-gray-900">{{ email.to_email }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-gray-500">Received:</span>
              <span class="text-gray-900">{{ formatDate(email.received_at) }}</span>
            </div>
          </div>
        </div>
        <button
          class="p-2 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0 ml-4"
          @click="handleClose"
        >
          <svg
            class="w-6 h-6 text-gray-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <!-- View Toggle -->
      <div class="px-6 py-3 border-b border-gray-200 bg-gray-50">
        <div class="flex gap-2">
          <button
            :class="[
              'px-4 py-2 rounded-lg font-medium transition-colors text-sm',
              viewMode === 'html'
                ? 'bg-blue-500 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-100'
            ]"
            @click="viewMode = 'html'"
          >
            HTML View
          </button>
          <button
            :class="[
              'px-4 py-2 rounded-lg font-medium transition-colors text-sm',
              viewMode === 'text'
                ? 'bg-blue-500 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-100'
            ]"
            @click="viewMode = 'text'"
          >
            Text View
          </button>
          <button
            class="ml-auto px-4 py-2 bg-white hover:bg-gray-100 text-gray-700 rounded-lg transition-colors text-sm flex items-center gap-2"
            @click="copyEmailContent"
          >
            <svg
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            </svg>
            Copy Content
          </button>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- HTML View -->
        <div
          v-if="viewMode === 'html'"
          class="prose max-w-none"
        >
          <!-- sanitizedHtml is run through DOMPurify (see <script>); see eslint override -->
          <div
            v-if="email.body_html"
            v-html="sanitizedHtml"
          />
          <div
            v-else
            class="text-gray-500 italic"
          >
            No HTML content available
          </div>
        </div>

        <!-- Text View -->
        <div
          v-else
          class="font-mono text-sm whitespace-pre-wrap text-gray-900"
        >
          <div v-if="email.body_text">
            {{ email.body_text }}
          </div>
          <div
            v-else
            class="text-gray-500 italic font-sans"
          >
            No text content available
          </div>
        </div>
      </div>

      <!-- Footer with metadata -->
      <div class="px-6 py-4 border-t border-gray-200 bg-gray-50">
        <div class="grid grid-cols-2 gap-4 text-xs text-gray-600">
          <div>
            <span class="font-medium">Message ID:</span>
            <code class="ml-2 text-gray-900 break-all">{{ email.message_id }}</code>
          </div>
          <div>
            <span class="font-medium">Email ID:</span>
            <code class="ml-2 text-gray-900">{{ email.id }}</code>
          </div>
        </div>
      </div>

      <!-- Copy Notification -->
      <div
        v-if="showCopyNotification"
        class="absolute top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg transition-opacity"
      >
        Copied to clipboard!
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import DOMPurify from 'dompurify';
import { decodeEmailHeader as decodeHeader } from '../utils/emailHeaders';
import { copyText } from '../utils/clipboard';
import { formatDateTime as formatDate } from '../utils/date';

const props = defineProps({
  email: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(['close']);

const viewMode = ref('html');
const showCopyNotification = ref(false);

// Sanitize attacker-controlled email HTML with DOMPurify before rendering.
// Email bodies are untrusted input; naive script-stripping is not enough (onerror=,
// javascript: URLs, SVG payloads, etc.). See docs/security.md.
const sanitizedHtml = computed(() => {
  if (!props.email.body_html) return '';

  const clean = DOMPurify.sanitize(props.email.body_html, {
    // Drop entire tag + content for these, and forbid event handlers.
    FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed', 'form'],
    FORBID_ATTR: ['srcset'],
    ALLOW_DATA_ATTR: false,
    // Only allow safe URL schemes (no javascript:, data: for scripts, etc.).
    ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|tel|cid):|[^a-z]|[a-z+.-]+(?:[^a-z+.:-]|$))/i,
  });

  return `<div class="email-content">${clean}</div>`;
});

function handleClose() {
  emit('close');
}

async function copyEmailContent() {
  const content = viewMode.value === 'html'
    ? props.email.body_html || props.email.body_text
    : props.email.body_text || props.email.body_html;

  if (content && (await copyText(content))) {
    showCopyNotification.value = true;
    setTimeout(() => {
      showCopyNotification.value = false;
    }, 2000);
  }
}
</script>

<style scoped>
/* Additional styling for email content */
:deep(.email-content) {
  font-family: system-ui, -apple-system, sans-serif;
  line-height: 1.6;
}

:deep(.email-content img) {
  max-width: 100%;
  height: auto;
}

:deep(.email-content a) {
  color: #2563eb;
  text-decoration: underline;
}
</style>
