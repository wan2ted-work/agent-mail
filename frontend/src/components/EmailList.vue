<template>
  <div class="bg-white rounded-lg shadow-lg overflow-hidden">
    <!-- Header -->
    <div class="p-6 border-b border-gray-200">
      <div class="flex items-center justify-between">
        <h3 class="text-lg font-semibold text-gray-900">
          Emails ({{ store.emailsPagination.total }})
        </h3>
        <button
          @click="handleRefresh"
          :disabled="store.loading"
          class="p-2 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
          title="Refresh"
        >
          <svg
            class="w-5 h-5 text-gray-600"
            :class="{ 'animate-spin': store.loading }"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Email List -->
    <div v-if="store.loading && !store.hasEmails" class="p-8 text-center text-gray-500">
      Loading emails...
    </div>

    <div v-else-if="!store.hasEmails" class="p-8 text-center text-gray-500">
      No emails found
    </div>

    <div v-else class="divide-y divide-gray-200">
      <div
        v-for="email in store.emails"
        :key="email.id"
        @click="handleEmailClick(email.id)"
        class="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1 min-w-0">
            <!-- From -->
            <div class="flex items-center gap-2 mb-1">
              <p class="text-sm font-semibold text-gray-900 truncate">
                {{ decodeHeader(email.from_name) || email.from_email }}
              </p>
              <span v-if="email.from_name" class="text-xs text-gray-500 truncate">
                &lt;{{ email.from_email }}&gt;
              </span>
            </div>

            <!-- Subject -->
            <p class="text-sm font-medium text-gray-900 mb-1 truncate">
              {{ decodeHeader(email.subject) || '(No Subject)' }}
            </p>

            <!-- To & Key Info -->
            <div class="flex items-center gap-3 text-xs text-gray-500 mb-1">
              <div v-if="email.to_email" class="flex items-center gap-1">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                <span class="truncate">{{ email.to_email }}</span>
              </div>
              <div v-if="email.extracted_key" class="flex items-center gap-1">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
                <code class="font-mono font-semibold">{{ email.extracted_key }}</code>
              </div>
            </div>

            <!-- Date -->
            <p class="text-xs text-gray-500">
              {{ formatDate(email.received_at) }}
            </p>
          </div>
          <svg class="w-5 h-5 text-gray-400 flex-shrink-0 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="store.emailsPagination.total > 0" class="p-4 border-t border-gray-200 bg-gray-50">
      <div class="flex items-center justify-between">
        <div class="text-sm text-gray-600">
          Showing {{ store.emailsPagination.skip + 1 }} -
          {{ Math.min(store.emailsPagination.skip + store.emailsPagination.limit, store.emailsPagination.total) }}
          of {{ store.emailsPagination.total }}
        </div>
        <div class="flex gap-2">
          <button
            @click="handlePrevPage"
            :disabled="store.emailsPagination.skip === 0 || store.loading"
            class="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <button
            @click="handleNextPage"
            :disabled="store.emailsPagination.skip + store.emailsPagination.limit >= store.emailsPagination.total || store.loading"
            class="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAppStore } from '../stores/appStore';
import { decodeEmailHeader } from '../utils/emailHeaders';

const store = useAppStore();

const emit = defineEmits(['email-click']);

function decodeHeader(text) {
  return decodeEmailHeader(text);
}

function handleEmailClick(emailId) {
  emit('email-click', emailId);
}

function handleRefresh() {
  store.loadEmails();
}

function handlePrevPage() {
  store.prevPage();
}

function handleNextPage() {
  store.nextPage();
}

function formatDate(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
</script>
