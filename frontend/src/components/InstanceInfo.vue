<template>
  <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
    <!-- Header -->
    <div class="flex items-start justify-between mb-6">
      <div class="flex-1">
        <h2 class="text-2xl font-bold text-gray-900">
          {{ store.instance.description || `${APP_NAME} Instance` }}
        </h2>
        <code class="text-xs text-gray-500">{{ store.instance.id }}</code>
      </div>
      <button
        class="px-4 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
        @click="handleLogout"
      >
        Disconnect
      </button>
    </div>

    <!-- Stats -->
    <div class="flex items-center gap-6 text-sm mb-6 pb-6 border-b border-gray-200">
      <div>
        <span class="text-gray-500">Total Emails:</span>
        <span class="ml-2 font-semibold text-gray-900">{{ store.instance.email_count || 0 }}</span>
      </div>
      <div>
        <span class="text-gray-500">Keys:</span>
        <span class="ml-2 font-semibold text-gray-900">{{ store.instanceKeys.length }}</span>
      </div>
      <div>
        <span class="text-gray-500">Status:</span>
        <span
          :class="[
            'ml-2 px-2 py-1 rounded-full text-xs font-medium',
            store.instance.is_active
              ? 'bg-green-100 text-green-800'
              : 'bg-red-100 text-red-800'
          ]"
        >
          {{ store.instance.is_active ? 'Active' : 'Inactive' }}
        </span>
      </div>
      <div>
        <span class="text-gray-500">Created:</span>
        <span class="ml-2 text-gray-900">{{ formatDate(store.instance.created_at) }}</span>
      </div>
    </div>

    <!-- Keys Section -->
    <div class="mb-6">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-lg font-semibold text-gray-900">
          Email Keys (Domains)
        </h3>
        <button
          class="px-3 py-1 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
          @click="showAddKey = !showAddKey"
        >
          + Add Key
        </button>
      </div>

      <!-- Add Key Form -->
      <div
        v-if="showAddKey"
        class="bg-gray-50 rounded-lg p-4 mb-4"
      >
        <form
          class="flex gap-2"
          @submit.prevent="handleAddKey"
        >
          <input
            v-model="newKey"
            type="text"
            placeholder="myproject"
            class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          >
          <button
            type="submit"
            :disabled="store.loading.mutation"
            class="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            Add
          </button>
          <button
            type="button"
            class="px-4 py-2 bg-gray-300 hover:bg-gray-400 text-gray-700 rounded-lg transition-colors"
            @click="showAddKey = false; newKey = ''"
          >
            Cancel
          </button>
        </form>
        <p class="text-xs text-gray-500 mt-2">
          Email address will be: anything@<strong>{{ newKey || 'key' }}</strong>.{{ EMAIL_DOMAIN }}
        </p>
      </div>

      <!-- Keys List -->
      <div
        v-if="store.instanceKeys.length > 0"
        class="space-y-2"
      >
        <div
          v-for="keyObj in store.instanceKeys"
          :key="keyObj.id"
          class="bg-gray-50 rounded-lg p-4 flex items-center justify-between"
        >
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-1">
              <code class="text-sm font-mono font-semibold text-gray-900">{{ keyObj.key }}</code>
              <button
                class="p-1 hover:bg-gray-200 rounded transition-colors"
                title="Copy email address"
                @click="copyToClipboard(keyAddress(keyObj.key))"
              >
                <svg
                  class="w-4 h-4 text-gray-600"
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
              </button>
            </div>
            <p class="text-xs text-gray-500">
              Email: {{ keyAddress(keyObj.key) }}
            </p>
            <p class="text-xs text-gray-400">
              Added: {{ formatDate(keyObj.created_at) }}
            </p>
          </div>
          <button
            :disabled="store.loading.mutation"
            class="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
            @click="handleRemoveKey(keyObj.key)"
          >
            Remove
          </button>
        </div>
      </div>

      <div
        v-else
        class="bg-yellow-50 border-l-4 border-yellow-400 rounded-lg p-4"
      >
        <div class="flex items-start">
          <svg
            class="w-6 h-6 text-yellow-600 mr-3 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <div class="flex-1">
            <h4 class="text-sm font-semibold text-yellow-800 mb-1">
              No keys added yet!
            </h4>
            <p class="text-sm text-yellow-700 mb-3">
              You need to add at least one key to start receiving emails. Click <strong>"+ Add Key"</strong> button above to create your first email domain.
            </p>
            <div class="bg-yellow-100 rounded p-3 text-xs text-yellow-800">
              <p class="font-semibold mb-1">
                Example:
              </p>
              <p>If you add key "<strong>myproject</strong>", you'll receive emails at:</p>
              <code class="block mt-1 bg-white px-2 py-1 rounded">{{ keyAddress('myproject') }}</code>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Custom Domains Section -->
    <CustomDomains />

    <!-- Secret Section -->
    <div class="bg-gray-50 rounded-lg p-4">
      <div class="text-sm text-gray-500 mb-1">
        Secret (API Key)
      </div>
      <div class="flex items-center gap-2">
        <code class="text-xs font-mono text-gray-900 truncate flex-1">{{ store.secret }}</code>
        <button
          class="p-1 hover:bg-gray-200 rounded transition-colors flex-shrink-0"
          title="Copy to clipboard"
          @click="copyToClipboard(store.secret)"
        >
          <svg
            class="w-4 h-4 text-gray-600"
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
        </button>
      </div>
      <p class="text-xs text-gray-500 mt-1">
        Use this UUID to access the API
      </p>
    </div>

    <!-- Notification -->
    <div
      v-if="showCopyNotification"
      class="fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg transition-opacity z-50"
    >
      {{ showCopyNotification }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useAppStore } from '../stores/appStore';
import CustomDomains from './CustomDomains.vue';
import { APP_NAME, EMAIL_DOMAIN, keyAddress } from '../config';
import { copyText } from '../utils/clipboard';
import { formatDate } from '../utils/date';

const store = useAppStore();
const showCopyNotification = ref(false);
const showAddKey = ref(false);
const newKey = ref('');

// Auto-open add key form if no keys exist
onMounted(() => {
  if (store.instanceKeys.length === 0) {
    showAddKey.value = true;
  }
});

// Watch for keys changes to auto-open form if all keys are removed
watch(() => store.instanceKeys.length, (newLength) => {
  if (newLength === 0) {
    showAddKey.value = true;
  }
});

function handleLogout() {
  store.clearSecret();
}

async function handleAddKey() {
  if (!newKey.value.trim()) return;

  try {
    await store.addKey(newKey.value.trim());
    newKey.value = '';
    showAddKey.value = false;
    showNotification('Key added successfully!');
  } catch {
    // Error surfaced via store.error
  }
}

async function handleRemoveKey(key) {
  if (!confirm(`Are you sure you want to remove the key "${key}"?`)) return;

  try {
    await store.removeKey(key);
    showNotification('Key removed successfully!');
  } catch {
    // Error surfaced via store.error
  }
}

async function copyToClipboard(text) {
  const ok = await copyText(text);
  showNotification(ok ? 'Copied to clipboard!' : 'Copy failed');
}

function showNotification(message) {
  showCopyNotification.value = message;
  setTimeout(() => {
    showCopyNotification.value = false;
  }, 2000);
}
</script>
